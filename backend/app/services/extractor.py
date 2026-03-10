import json
import logging

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


class ProxiedSession(requests.Session):
    """A requests.Session that routes all requests through a Cloudflare Worker proxy."""

    def __init__(self, proxy_url: str):
        super().__init__()
        self.proxy_url = proxy_url.rstrip("/")

    def request(self, method, url, **kwargs):
        # Route all YouTube requests through the proxy worker
        if self.proxy_url and "youtube.com" in url:
            encoded_url = requests.utils.quote(url, safe="")
            proxied_url = f"{self.proxy_url}?url={encoded_url}"
            logger.info(f"Proxying {method} {url}")
            # Keep the same method (GET/POST) — worker handles both
            return super().request(method, proxied_url, **kwargs)
        return super().request(method, url, **kwargs)


def get_transcript(youtube_video_id: str) -> str:
    """Fetch transcript for a YouTube video."""
    if TRANSCRIPT_PROXY_URL:
        logger.info(f"Using proxy for transcript: {TRANSCRIPT_PROXY_URL}")
        session = ProxiedSession(TRANSCRIPT_PROXY_URL)
        ytt_api = YouTubeTranscriptApi(http_client=session)
    else:
        ytt_api = YouTubeTranscriptApi()
    result = ytt_api.fetch(youtube_video_id)
    parts = []
    for snippet in result.snippets:
        parts.append(f"[{snippet.start:.1f}s] {snippet.text}")
    return "\n".join(parts)


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
    # Strip markdown code fences if present
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]  # remove ```json line
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    return data.get("insights", [])


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
