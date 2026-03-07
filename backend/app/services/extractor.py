import json

import anthropic
from youtube_transcript_api import YouTubeTranscriptApi
from sqlalchemy.orm import Session

from app.config import ANTHROPIC_API_KEY
from app.models.models import Video, Insight

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
    "For each insight, provide the approximate timestamp range (in seconds) "
    "from the transcript where this insight was discussed.\n\n"
    'Respond in JSON format:\n'
    '{{\n'
    '    "video_type": "podcast_interview",\n'
    '    "summary_style": "key_takeaways",\n'
    '    "insights": [\n'
    '        {{\n'
    '            "insight_text": "The insight text here",\n'
    '            "category": "takeaway|action|quote",\n'
    '            "start_timestamp": 120.0,\n'
    '            "end_timestamp": 155.0\n'
    '        }}\n'
    '    ]\n'
    '}}\n\n'
    "VIDEO TITLE: {title}\n\n"
    "TRANSCRIPT:\n{transcript}"
)


def get_transcript(youtube_video_id: str) -> str:
    """Fetch transcript for a YouTube video."""
    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.fetch(youtube_video_id)
    parts = []
    for entry in transcript_list:
        timestamp = entry.start
        text = entry.text
        parts.append(f"[{timestamp:.1f}s] {text}")
    return "\n".join(parts)


def call_claude(prompt: str) -> str:
    """Call Claude API to analyze transcript."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def parse_claude_response(response_text: str) -> list[dict]:
    """Parse Claude's JSON response into a list of insights."""
    try:
        data = json.loads(response_text)
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
