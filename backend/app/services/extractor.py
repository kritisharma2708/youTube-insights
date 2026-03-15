import json
import logging
import re
import subprocess
import xml.etree.ElementTree as ET

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
# Method 2: Invidious API (community-run YouTube frontends)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Method 2: Direct HTML parsing — extract captions from the YouTube page
#            we already fetch successfully via proxy
# ---------------------------------------------------------------------------

def _transcript_via_html_parsing(video_id: str) -> str:
    """Parse captions directly from YouTube watch page HTML."""
    print("[METHOD 2] Direct HTML parsing", flush=True)

    # Fetch the watch page through proxy
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    if TRANSCRIPT_PROXY_URL:
        encoded = requests.utils.quote(watch_url, safe="")
        fetch_url = f"{TRANSCRIPT_PROXY_URL}?url={encoded}"
    else:
        fetch_url = watch_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(fetch_url, headers=headers, timeout=30)
    resp.raise_for_status()
    html = resp.text
    print(f"[METHOD 2] Page fetched, length={len(html)}", flush=True)

    # Try to find ytInitialPlayerResponse in the HTML
    caption_url = None

    # Pattern 1: ytInitialPlayerResponse = {...}
    match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.+?\});', html)
    if match:
        try:
            player_data = json.loads(match.group(1))
            print(f"[METHOD 2] Found ytInitialPlayerResponse, keys: {list(player_data.keys())}", flush=True)
            caption_url = _extract_caption_url(player_data)
        except json.JSONDecodeError as e:
            print(f"[METHOD 2] Failed to parse ytInitialPlayerResponse: {e}", flush=True)

    # Pattern 2: Look for caption URLs directly in HTML
    if not caption_url:
        # Caption URLs contain "timedtext" and "lang=en"
        matches = re.findall(r'(https?://[^"]*timedtext[^"]*)', html)
        for url in matches:
            url = url.replace('\\u0026', '&')
            if 'lang=en' in url or 'lang%3Den' in url:
                caption_url = url
                print(f"[METHOD 2] Found caption URL in HTML directly", flush=True)
                break
        # Fallback: take first timedtext URL
        if not caption_url and matches:
            caption_url = matches[0].replace('\\u0026', '&')
            print(f"[METHOD 2] Using first timedtext URL found", flush=True)

    if not caption_url:
        # Log what we found for debugging
        has_captions = '"captions"' in html
        has_timedtext = 'timedtext' in html
        print(f"[METHOD 2] No caption URL found. captions_in_html={has_captions}, timedtext_in_html={has_timedtext}", flush=True)
        raise RuntimeError(f"No caption URL found in page HTML (captions={has_captions}, timedtext={has_timedtext})")

    # Fetch the caption file (timedtext URLs are usually on a different domain)
    caption_url_clean = caption_url.replace('\\u0026', '&')
    # Add json3 format if not already specified
    if 'fmt=' not in caption_url_clean:
        caption_url_clean += '&fmt=json3'

    print(f"[METHOD 2] Fetching captions from: {caption_url_clean[:100]}...", flush=True)
    cap_resp = requests.get(caption_url_clean, timeout=30)
    cap_resp.raise_for_status()

    transcript = _parse_caption_xml(cap_resp.text)
    if not transcript:
        raise RuntimeError("Caption file was empty")

    return transcript


def _extract_caption_url(player_data: dict):
    """Extract English caption URL from ytInitialPlayerResponse."""
    captions = player_data.get("captions", {})
    renderer = captions.get("playerCaptionsTracklistRenderer", {})
    tracks = renderer.get("captionTracks", [])

    if not tracks:
        return None

    # Find English track
    for track in tracks:
        lang = track.get("languageCode", "")
        if lang.startswith("en"):
            return track.get("baseUrl")

    # Fallback to first track
    if tracks:
        return tracks[0].get("baseUrl")

    return None


def _parse_caption_xml(xml_text: str) -> str:
    """Parse YouTube caption XML into timestamped transcript."""
    parts = []
    try:
        root = ET.fromstring(xml_text)
        for elem in root.findall('.//text'):
            start = float(elem.get('start', 0))
            text = elem.text or ''
            text = text.replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"')
            text = text.strip()
            if text:
                parts.append(f"[{start:.1f}s] {text}")
    except ET.ParseError:
        # Try json3 format
        try:
            data = json.loads(xml_text)
            for event in data.get("events", []):
                start_ms = event.get("tStartMs", 0)
                start_sec = start_ms / 1000.0
                segs = event.get("segs", [])
                text = "".join(s.get("utf8", "") for s in segs).strip()
                if text and text != "\n":
                    parts.append(f"[{start_sec:.1f}s] {text}")
        except (json.JSONDecodeError, KeyError):
            pass

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Method 3: yt-dlp with web client (no proxy, uses its own anti-detection)
# ---------------------------------------------------------------------------

def _transcript_via_ytdlp(video_id: str) -> str:
    print("[METHOD 3] yt-dlp subtitles", flush=True)
    url = f"https://www.youtube.com/watch?v={video_id}"

    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "en",
        "--sub-format", "json3",
        "--dump-json",
        "--extractor-args", "youtube:player_client=web",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr[:300]}")

    info = json.loads(result.stdout)

    subs = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})

    sub_url = None
    for lang_key in ["en", "en-US", "en-GB"]:
        for source in [subs, auto_subs]:
            if lang_key in source:
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

    print(f"[METHOD 3] Fetching subtitle from: {sub_url[:80]}...", flush=True)
    resp = requests.get(sub_url, timeout=30)
    resp.raise_for_status()

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
# Main transcript fetcher with fallback chain
# ---------------------------------------------------------------------------

def get_transcript(youtube_video_id: str) -> str:
    """Fetch transcript using a fallback chain of methods."""
    methods = [
        ("youtube-transcript-api", _transcript_via_ytt_api),
        ("html-parsing", _transcript_via_html_parsing),
        ("yt-dlp", _transcript_via_ytdlp),
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
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def parse_claude_response(response_text: str) -> list[dict]:
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
