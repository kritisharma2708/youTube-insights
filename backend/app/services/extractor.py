import json
import logging
import re
import subprocess
import tempfile

import anthropic
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from sqlalchemy.orm import Session

from app.config import ANTHROPIC_API_KEY, TRANSCRIPT_PROXY_URL
from app.models.models import Video, Insight

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = (
    "You are an expert content analyst. Analyze the following video transcript "
    "and extract the most valuable insights.\n\n"
    "First, identify the type of video (podcast interview, business case study, "
    "lecture, deep-dive conversation, etc.).\n"
    "Then, automatically decide the best summary style:\n"
    "- For interviews/podcasts: focus on key takeaways and quotable moments\n"
    "- For tutorials/how-tos: focus on actionable advice\n"
    "- For case studies: focus on key takeaways and lessons learned\n"
    "- For debates/discussions: focus on contrasting viewpoints and quotable moments\n\n"
    "Extract 5-10 of the BEST insights. Each insight should be:\n"
    "- Concise (1-3 sentences)\n"
    "- Self-contained (understandable without context)\n"
    "- Valuable (teaches something, inspires action, or captures a powerful idea)\n\n"
    "For each insight, provide:\n"
    "- The approximate timestamp range (in seconds) from the transcript\n"
    "- A source_quote: the EXACT verbatim words from the transcript that support "
    "this insight (copy-paste the speaker's actual words, not a paraphrase)\n\n"
    'Respond in JSON format:\n'
    '{{\n'
    '    "video_type": "podcast_interview",\n'
    '    "summary_style": "key_takeaways",\n'
    '    "insights": [\n'
    '        {{\n'
    '            "insight_text": "The insight text here",\n'
    '            "source_quote": "The exact words from the transcript...",\n'
    '            "category": "takeaway|action|quote",\n'
    '            "start_timestamp": 120.0,\n'
    '            "end_timestamp": 155.0\n'
    '        }}\n'
    '    ]\n'
    '}}\n\n'
    "VIDEO TITLE: {title}\n\n"
    "TRANSCRIPT:\n{transcript}"
)


# ---------------------------------------------------------------------------
# Proxy session for routing requests through Cloudflare Worker
# ---------------------------------------------------------------------------

class ProxiedSession(requests.Session):
    """A requests.Session that routes all requests through a Cloudflare Worker proxy."""

    def __init__(self, proxy_url: str):
        super().__init__()
        self.proxy_url = proxy_url.rstrip("/")

    def request(self, method, url, **kwargs):
        if self.proxy_url and "youtube.com" in url:
            encoded_url = requests.utils.quote(url, safe="")
            proxied_url = f"{self.proxy_url}?url={encoded_url}"
            print(f"[PROXY] {method} {url}", flush=True)
            resp = super().request(method, proxied_url, **kwargs)
            print(f"[PROXY] Response: {resp.status_code}, length={len(resp.text)}", flush=True)
            return resp
        return super().request(method, url, **kwargs)


# ---------------------------------------------------------------------------
# Method 1: youtube-transcript-api (with proxy)
# ---------------------------------------------------------------------------

def _transcript_via_ytt_api(video_id: str) -> str:
    """Fetch transcript using youtube-transcript-api library."""
    print("[METHOD 1] youtube-transcript-api", flush=True)
    if TRANSCRIPT_PROXY_URL:
        session = ProxiedSession(TRANSCRIPT_PROXY_URL)
        ytt_api = YouTubeTranscriptApi(http_client=session)
    else:
        ytt_api = YouTubeTranscriptApi()
    result = ytt_api.fetch(video_id)
    parts = []
    for snippet in result.snippets:
        parts.append(f"[{snippet.start:.1f}s] {snippet.text}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Method 2: yt-dlp subtitle extraction
# ---------------------------------------------------------------------------

def _transcript_via_ytdlp(video_id: str) -> str:
    """Fetch transcript using yt-dlp subtitle extraction."""
    print("[METHOD 2] yt-dlp subtitles", flush=True)
    url = f"https://www.youtube.com/watch?v={video_id}"

    # Use yt-dlp to dump subtitle info as JSON
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "en",
        "--sub-format", "json3",
        "--dump-json",
        url,
    ]

    # If we have a proxy URL, use it
    if TRANSCRIPT_PROXY_URL:
        cmd.insert(1, f"--proxy={TRANSCRIPT_PROXY_URL}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr[:300]}")

    info = json.loads(result.stdout)

    # Try manual subtitles first, then auto-generated
    subs = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})

    sub_url = None
    for lang_key in ["en", "en-US", "en-GB"]:
        for source in [subs, auto_subs]:
            if lang_key in source:
                # Find json3 format, fallback to first available
                formats = source[lang_key]
                for fmt in formats:
                    if fmt.get("ext") == "json3":
                        sub_url = fmt["url"]
                        break
                if not sub_url and formats:
                    sub_url = formats[0]["url"]
                if sub_url:
                    break
        if sub_url:
            break

    if not sub_url:
        raise RuntimeError("No English subtitles found via yt-dlp")

    print(f"[METHOD 2] Fetching subtitle from: {sub_url[:80]}...", flush=True)
    resp = requests.get(sub_url, timeout=30)
    resp.raise_for_status()

    # Parse json3 format
    sub_data = resp.json()
    parts = []
    for event in sub_data.get("events", []):
        start_ms = event.get("tStartMs", 0)
        start_sec = start_ms / 1000.0
        segs = event.get("segs", [])
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if text and text != "\n":
            parts.append(f"[{start_sec:.1f}s] {text}")

    if not parts:
        raise RuntimeError("yt-dlp subtitles were empty")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Method 3: Custom Android innertube client
# ---------------------------------------------------------------------------

def _transcript_via_android_innertube(video_id: str) -> str:
    """Fetch transcript using Android innertube client context."""
    print("[METHOD 3] Android innertube client", flush=True)

    # Step 1: POST to innertube with Android client context
    innertube_url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.09.37",
                "androidSdkVersion": 30,
                "hl": "en",
                "gl": "US",
            }
        },
        "videoId": video_id,
    }
    headers = {
        "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
        "Content-Type": "application/json",
    }

    # Route through proxy if available
    if TRANSCRIPT_PROXY_URL:
        encoded_url = requests.utils.quote(innertube_url, safe="")
        request_url = f"{TRANSCRIPT_PROXY_URL}?url={encoded_url}"
    else:
        request_url = innertube_url

    resp = requests.post(request_url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    player_data = resp.json()

    print(f"[METHOD 3] Player response keys: {list(player_data.keys())}", flush=True)

    # Step 2: Extract caption track URL from player response
    captions = player_data.get("captions", {})
    renderer = captions.get("playerCaptionsTracklistRenderer", {})
    tracks = renderer.get("captionTracks", [])

    if not tracks:
        raise RuntimeError(
            f"No caption tracks in Android innertube response. "
            f"Keys: {list(player_data.keys())}"
        )

    # Find English track
    caption_url = None
    for track in tracks:
        lang = track.get("languageCode", "")
        if lang.startswith("en"):
            caption_url = track.get("baseUrl")
            break

    # Fallback to first track if no English found
    if not caption_url and tracks:
        caption_url = tracks[0].get("baseUrl")

    if not caption_url:
        raise RuntimeError("No caption URL found in tracks")

    # Request JSON3 format for easier parsing
    caption_url += "&fmt=json3"
    print(f"[METHOD 3] Fetching captions from: {caption_url[:80]}...", flush=True)

    # Fetch captions (these URLs are on timedtext.video.google.com, usually not blocked)
    caption_resp = requests.get(caption_url, timeout=30)
    caption_resp.raise_for_status()
    sub_data = caption_resp.json()

    parts = []
    for event in sub_data.get("events", []):
        start_ms = event.get("tStartMs", 0)
        start_sec = start_ms / 1000.0
        segs = event.get("segs", [])
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if text and text != "\n":
            parts.append(f"[{start_sec:.1f}s] {text}")

    if not parts:
        raise RuntimeError("Android innertube captions were empty")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main transcript fetcher with fallback chain
# ---------------------------------------------------------------------------

def get_transcript(youtube_video_id: str) -> str:
    """Fetch transcript using a fallback chain of methods."""
    methods = [
        ("youtube-transcript-api", _transcript_via_ytt_api),
        ("yt-dlp", _transcript_via_ytdlp),
        ("android-innertube", _transcript_via_android_innertube),
    ]

    errors = []
    for name, method in methods:
        try:
            transcript = method(youtube_video_id)
            print(f"[TRANSCRIPT] Success with {name}!", flush=True)
            return transcript
        except Exception as e:
            print(f"[TRANSCRIPT] {name} failed: {e}", flush=True)
            errors.append(f"{name}: {e}")

    raise RuntimeError(
        "All transcript methods failed:\n" + "\n".join(errors)
    )


# ---------------------------------------------------------------------------
# Claude analysis
# ---------------------------------------------------------------------------

def call_claude(prompt: str) -> str:
    """Call Claude API to analyze transcript."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def parse_claude_response(response_text: str) -> list[dict]:
    """Parse Claude's JSON response into a list of insights."""
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    return data.get("insights", [])


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------

def extract_insights(db: Session, video_id: int) -> list[Insight]:
    """Extract insights from a video's transcript using Claude."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return []

    transcript = get_transcript(video.youtube_video_id)
    prompt = EXTRACTION_PROMPT_TEMPLATE.format(title=video.title, transcript=transcript)
    response = call_claude(prompt)
    raw_insights = parse_claude_response(response)

    insights = []
    for i, raw in enumerate(raw_insights):
        insight = Insight(
            video_id=video.id,
            insight_text=raw["insight_text"],
            source_quote=raw.get("source_quote", ""),
            category=raw["category"],
            start_timestamp=raw["start_timestamp"],
            end_timestamp=raw["end_timestamp"],
            order=i,
        )
        db.add(insight)
        insights.append(insight)

    video.processed = True
    db.commit()
    return insights
