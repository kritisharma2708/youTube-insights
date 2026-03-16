import json
import logging
import re
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

import time

import anthropic
import feedparser
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from sqlalchemy.orm import Session

from app.config import ANTHROPIC_API_KEY, ASSEMBLYAI_API_KEY, TRANSCRIPT_PROXY_URL
from app.models.models import Channel, Video, Insight

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
# Method 1: Podcast RSS + AssemblyAI transcription
# ---------------------------------------------------------------------------

def _transcript_via_podcast(video: Video) -> str:
    """Fetch transcript by matching video to podcast episode and transcribing audio."""
    channel = video.channel
    if not channel or not channel.podcast_rss_url:
        raise RuntimeError("Channel has no podcast RSS URL")

    if not ASSEMBLYAI_API_KEY:
        raise RuntimeError("ASSEMBLYAI_API_KEY not set")

    print(f"[METHOD 1] Podcast RSS + AssemblyAI for: {video.title}", flush=True)

    # Step 1: Fetch and parse RSS feed
    print(f"[METHOD 1] Fetching RSS: {channel.podcast_rss_url}", flush=True)
    feed = feedparser.parse(channel.podcast_rss_url)

    if not feed.entries:
        raise RuntimeError("RSS feed has no entries")

    print(f"[METHOD 1] Found {len(feed.entries)} episodes in RSS feed", flush=True)

    # Step 2: Match video title to podcast episode
    audio_url = _find_matching_episode(video.title, feed.entries)

    if not audio_url:
        raise RuntimeError(f"No matching podcast episode found for: {video.title}")

    print(f"[METHOD 1] Matched audio: {audio_url[:80]}...", flush=True)

    # Step 3: Transcribe with AssemblyAI (raw HTTP API)
    print(f"[METHOD 1] Sending to AssemblyAI for transcription...", flush=True)
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    resp = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json={"audio_url": audio_url, "speech_models": ["universal-2"]},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    transcript_id = resp.json()["id"]
    print(f"[METHOD 1] Transcript ID: {transcript_id}, polling...", flush=True)

    # Poll for completion
    for _ in range(120):  # max ~10 min
        poll = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers,
            timeout=30,
        )
        poll.raise_for_status()
        data = poll.json()
        if data["status"] == "completed":
            break
        elif data["status"] == "error":
            raise RuntimeError(f"AssemblyAI error: {data.get('error')}")
        time.sleep(5)
    else:
        raise RuntimeError("AssemblyAI transcription timed out")

    # Step 4: Format transcript with timestamps
    parts = []
    words = data.get("words", [])
    if words:
        current_start = 0.0
        current_words = []
        for word in words:
            if not current_words:
                current_start = word["start"] / 1000.0
            current_words.append(word["text"])
            if (word["text"].endswith(('.', '?', '!')) and len(current_words) > 5) or len(current_words) >= 15:
                parts.append(f"[{current_start:.1f}s] {' '.join(current_words)}")
                current_words = []
        if current_words:
            parts.append(f"[{current_start:.1f}s] {' '.join(current_words)}")
    elif data.get("text"):
        parts.append(f"[0.0s] {data['text']}")

    if not parts:
        raise RuntimeError("AssemblyAI returned empty transcript")

    print(f"[METHOD 1] Transcription complete: {len(parts)} segments", flush=True)
    return "\n".join(parts)


def _find_matching_episode(video_title: str, entries: list) -> str:
    """Find the podcast episode that best matches the video title."""
    video_title_lower = video_title.lower()

    best_match = None
    best_score = 0.0

    for entry in entries:
        episode_title = entry.get("title", "")
        # Calculate title similarity
        score = SequenceMatcher(None, video_title_lower, episode_title.lower()).ratio()

        if score > best_score:
            best_score = score
            # Get audio URL from enclosures
            audio_url = None
            for link in entry.get("links", []):
                if link.get("type", "").startswith("audio/"):
                    audio_url = link.get("href")
                    break
            # Also check enclosures
            if not audio_url:
                for enc in entry.get("enclosures", []):
                    if enc.get("type", "").startswith("audio/"):
                        audio_url = enc.get("href")
                        break
            if audio_url:
                best_match = audio_url

    # Require at least 40% title similarity
    if best_score >= 0.4 and best_match:
        print(f"[METHOD 1] Best match score: {best_score:.2f}", flush=True)
        return best_match

    # Fallback: try keyword matching
    for entry in entries:
        episode_title = entry.get("title", "").lower()
        # Check if key words from video title appear in episode title
        video_words = set(video_title_lower.split())
        episode_words = set(episode_title.split())
        # Remove common words
        stop_words = {"the", "a", "an", "is", "in", "on", "at", "to", "for", "of", "and", "or", "|", "-", "with"}
        video_words -= stop_words
        episode_words -= stop_words
        overlap = video_words & episode_words
        if len(overlap) >= 3:
            for link in entry.get("links", []):
                if link.get("type", "").startswith("audio/"):
                    print(f"[METHOD 1] Keyword match ({len(overlap)} words): {entry.get('title')}", flush=True)
                    return link.get("href")
            for enc in entry.get("enclosures", []):
                if enc.get("type", "").startswith("audio/"):
                    print(f"[METHOD 1] Keyword match ({len(overlap)} words): {entry.get('title')}", flush=True)
                    return enc.get("href")

    return None


# ---------------------------------------------------------------------------
# Method 2: youtube-transcript-api (with proxy)
# ---------------------------------------------------------------------------

def _transcript_via_ytt_api(video_id: str) -> str:
    print("[METHOD 2] youtube-transcript-api", flush=True)
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
# Method 3: Direct HTML parsing
# ---------------------------------------------------------------------------

def _transcript_via_html_parsing(video_id: str) -> str:
    print("[METHOD 3] Direct HTML parsing", flush=True)

    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    if TRANSCRIPT_PROXY_URL:
        encoded = requests.utils.quote(watch_url, safe="")
        fetch_url = f"{TRANSCRIPT_PROXY_URL}?url={encoded}"
    else:
        fetch_url = watch_url

    resp = requests.get(fetch_url, timeout=30)
    resp.raise_for_status()
    html = resp.text

    caption_url = None

    match = re.search(r'ytInitialPlayerResponse\s*=\s*(\{.+?\});', html)
    if match:
        try:
            player_data = json.loads(match.group(1))
            caption_url = _extract_caption_url(player_data)
        except json.JSONDecodeError:
            pass

    if not caption_url:
        matches = re.findall(r'(https?://[^"]*timedtext[^"]*)', html)
        for url in matches:
            url = url.replace('\\u0026', '&')
            if 'lang=en' in url:
                caption_url = url
                break
        if not caption_url and matches:
            caption_url = matches[0].replace('\\u0026', '&')

    if not caption_url:
        raise RuntimeError("No caption URL found in page HTML")

    caption_url_clean = caption_url.replace('\\u0026', '&')
    if 'fmt=' not in caption_url_clean:
        caption_url_clean += '&fmt=json3'

    cap_resp = requests.get(caption_url_clean, timeout=30)
    cap_resp.raise_for_status()

    transcript = _parse_caption_xml(cap_resp.text)
    if not transcript:
        raise RuntimeError("Caption file was empty")

    return transcript


def _extract_caption_url(player_data: dict):
    captions = player_data.get("captions", {})
    renderer = captions.get("playerCaptionsTracklistRenderer", {})
    tracks = renderer.get("captionTracks", [])
    if not tracks:
        return None
    for track in tracks:
        if track.get("languageCode", "").startswith("en"):
            return track.get("baseUrl")
    return tracks[0].get("baseUrl") if tracks else None


def _parse_caption_xml(xml_text: str) -> str:
    parts = []
    try:
        root = ET.fromstring(xml_text)
        for elem in root.findall('.//text'):
            start = float(elem.get('start', 0))
            text = (elem.text or '').strip()
            if text:
                parts.append(f"[{start:.1f}s] {text}")
    except ET.ParseError:
        try:
            data = json.loads(xml_text)
            for event in data.get("events", []):
                start_sec = event.get("tStartMs", 0) / 1000.0
                segs = event.get("segs", [])
                text = "".join(s.get("utf8", "") for s in segs).strip()
                if text and text != "\n":
                    parts.append(f"[{start_sec:.1f}s] {text}")
        except (json.JSONDecodeError, KeyError):
            pass
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main transcript fetcher with fallback chain
# ---------------------------------------------------------------------------

def get_transcript(video: Video) -> str:
    """Fetch transcript using a fallback chain of methods."""
    errors = []

    # Method 1: Podcast RSS + AssemblyAI (best for podcast channels)
    if video.channel and video.channel.podcast_rss_url and ASSEMBLYAI_API_KEY:
        try:
            transcript = _transcript_via_podcast(video)
            print(f"[TRANSCRIPT] Success with podcast RSS + AssemblyAI!", flush=True)
            return transcript
        except Exception as e:
            print(f"[TRANSCRIPT] podcast failed: {e}", flush=True)
            errors.append(f"podcast: {e}")

    # Method 2: youtube-transcript-api (works locally, blocked on cloud)
    try:
        transcript = _transcript_via_ytt_api(video.youtube_video_id)
        print(f"[TRANSCRIPT] Success with youtube-transcript-api!", flush=True)
        return transcript
    except Exception as e:
        print(f"[TRANSCRIPT] youtube-transcript-api failed: {e}", flush=True)
        errors.append(f"youtube-transcript-api: {e}")

    # Method 3: Direct HTML parsing
    try:
        transcript = _transcript_via_html_parsing(video.youtube_video_id)
        print(f"[TRANSCRIPT] Success with html-parsing!", flush=True)
        return transcript
    except Exception as e:
        print(f"[TRANSCRIPT] html-parsing failed: {e}", flush=True)
        errors.append(f"html-parsing: {e}")

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

    transcript = get_transcript(video)
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
