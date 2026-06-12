"""Gemini integration for lesson note generation and RAG chat."""
from __future__ import annotations

import google.generativeai as genai

from app.core.config import settings


# Configured lazily so unit tests / imports don't require the key.
_model = None


def _get_model():
    global _model
    if _model is None:
        if not settings.gemini_api_key or settings.gemini_api_key == "your-gemini-api-key":
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to backend/.env before processing videos."
            )
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(settings.gemini_model)
    return _model


LESSON_NOTES_PROMPT = """You are an expert tutor. Given a video transcript (with timestamps), produce
comprehensive lesson notes in Markdown using EXACTLY this structure:

# Lesson Summary
(2-4 sentence high-level overview)

## Main Topics
(Bulleted list of the main topics covered, in order)

## Important Concepts
(Bulleted list of key concepts, each with a one-line definition)

## Detailed Notes
(In-depth, well-organized notes broken into sub-sections. Use ## sub-headings.
Include the timestamp from the transcript inline like [00:12:34] when referencing
a specific moment. Be thorough — this should be study-quality material.)

## Examples
(Bulleted list of concrete examples from the lesson)

## Key Takeaways
(Bulleted list of the most important takeaways)

## Revision Notes
(A condensed 1-page-style summary suitable for last-minute review)

## Potential Interview Questions
(Numbered list of 5-10 likely interview questions about this content, with short answers)

## Practice Questions
(Numbered list of 5-10 practice/exercise questions to test understanding)

Rules:
- Use the transcript timestamps when they help anchor a point.
- Do NOT invent facts not present in the transcript. If something is unclear, say so briefly.
- Output ONLY the Markdown. No preamble, no closing remarks.
"""


def generate_lesson_notes(transcript: str, title: str) -> str:
    """Generate structured lesson notes from a transcript."""
    model = _get_model()
    prompt = f"{LESSON_NOTES_PROMPT}\n\nLesson title: {title}\n\nTranscript:\n```\n{transcript}\n```\n"
    response = model.generate_content(prompt)
    return response.text or ""


CHAT_SYSTEM_PROMPT = """You are a helpful tutor. Answer the user's question using ONLY the
transcript excerpts provided as context. If the answer is not in the context, say
"I don't have enough information in the transcript to answer that." Do not invent
facts. Cite relevant timestamps from the context (e.g. [00:12:34]) when useful.

When the user asks for things like "summarize", "generate quiz", "create flashcards",
or "explain chapter X", produce well-structured Markdown.
"""


def chat_with_context(question: str, context_chunks: list[str]) -> str:
    """Answer a question using retrieved transcript chunks as context."""
    model = _get_model()

    context_block = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no context)"

    # Gemini doesn't have a "system" role in the same way; fold the system prompt
    # into the first user turn.
    prompt = (
        f"{CHAT_SYSTEM_PROMPT}\n\n"
        f"Context (transcript excerpts):\n```\n{context_block}\n```\n\n"
        f"User question: {question}\n\nAnswer in Markdown."
    )
    response = model.generate_content(prompt)
    return response.text or ""
