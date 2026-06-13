"""Gemini integration for lesson note generation and RAG chat.

The lesson-notes generator uses a **map-reduce** strategy so it can handle
multi-hour videos (20k+ words) without blowing past Gemini's context window:

    1. MAP    — summarize each transcript chunk individually
                (key topics, key facts, important timestamps, examples).
    2. REDUCE — feed the full set of chunk summaries (plus a small window of
                the original transcript for each) to Gemini and ask it to
                produce the final structured Markdown lesson.

Chat already uses RAG over the chunked ChromaDB index.
"""
from __future__ import annotations

import logging
from typing import Iterable

import google.generativeai as genai

from app.services.vector_store import chunk_transcript, estimate_tokens

from app.core.config import settings


logger = logging.getLogger(__name__)


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
        # Slight temperature nudge above zero so the model doesn't fall into
        # a single deterministic phrasing loop on repeated questions. Top-p
        # is a soft cap on the long tail.
        _model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.9,
            ),
        )
    return _model


# ---------------------------------------------------------------------------
# Chunk-level summarisation (MAP step)
# ---------------------------------------------------------------------------

CHUNK_SUMMARY_PROMPT = """You're helping a tutor write lesson notes from a video. This is just
one chunk of a longer transcript — the tutor will combine your notes on this
chunk with notes from other chunks to build the full lesson.

Write a tight, useful summary in Markdown. Don't be a robot. Don't open with
"This chunk discusses…" — just get into it.

Use roughly this layout, but you can stretch or compress sections when the
content calls for it:

## What's in this part
A few sentences in your own words explaining what the speaker is actually
walking through. Not "the topic is X" — more like "the speaker starts by
contrasting X with Y, then walks through the proof."

## The stuff a student needs to remember
A bulleted list of the concrete claims, definitions, formulas, or rules
introduced. If the speaker says "the capital of X is Y", that goes here.
Keep numbers, names, and exact terms intact.

## Examples worth keeping
What the speaker actually uses to illustrate the idea, if any. If there
aren't any, just skip this section — no need for a header.

## Moments worth jumping back to
Up to 5 timestamps in [HH:MM:SS] format that mark a moment a student would
want to rewatch. The "aha" moments, the worked examples, the "here's the
trick" beats.

Keep it dense. Aim for 200-350 words. Don't invent anything that isn't in
the chunk. If the chunk is mostly filler (jokes, "um"s, logistics), it's
fine to write a short summary and move on.

Output the Markdown directly. No preamble, no "Sure, here's the summary:"."""


def _summarize_chunk(
    chunk: str,
    index: int,
    total: int,
    title: str,
    progress_cb=None,
) -> str:
    """MAP step: summarise a single transcript chunk."""
    model = _get_model()
    prompt = (
        f"{CHUNK_SUMMARY_PROMPT}\n\n"
        f"Lesson title: {title}\n"
        f"Chunk {index + 1} of {total}\n\n"
        f"Here's the transcript chunk:\n```\n{chunk}\n```"
    )
    try:
        resp = model.generate_content(prompt)
        if progress_cb:
            progress_cb(
                f"Summarizing chunk {index + 1}/{total}…",
                # Map step occupies 70–90% of the overall pipeline progress.
                70 + int(20 * (index + 1) / max(1, total)),
            )
        return (resp.text or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Chunk %d/%d summarization failed: %s", index + 1, total, exc)
        # Fall back to a minimal "raw" summary so the reduce step still has content.
        first_lines = "\n".join(chunk.splitlines()[:8])
        return (
            f"## Chunk topics\n- (auto-summary unavailable)\n\n"
            f"## Key facts & concepts\n- See transcript excerpt below.\n\n"
            f"## Notable examples\n- (none captured)\n\n"
            f"## Important timestamps\n- (none captured)\n\n"
            f"### Transcript excerpt\n```\n{first_lines}\n…\n```"
        )


# ---------------------------------------------------------------------------
# Final lesson assembly (REDUCE step)
# ---------------------------------------------------------------------------

LESSON_NOTES_PROMPT = """You're an experienced tutor writing study notes from a video. You'll get
a stack of chunk-level summaries (in order) plus a slice of the raw
transcript for context. Your job is to turn all of that into notes a student
would actually want to read.

Write in the same voice you'd use explaining the material to a smart friend
who missed class. Not a textbook. Not a corporate summary. Just clear,
honest, well-organized notes.

Use the section layout below as scaffolding, but don't be a slave to it.
Skip a section if the content doesn't earn it. Rename a section if a better
name fits. Combine sections if the material is thin. Stretch a section out
if the meat is there. The point is useful notes, not checkbox compliance.

# Lesson Summary
Two to four sentences that tell the reader what the video is actually about
and why they should care. No "This video discusses…" openings. Get to it.

## Main Topics
The throughline of the video, in order. A short bulleted list.

## Important Concepts
Key terms, definitions, and ideas a student would be expected to know after
watching. One line per concept. If a concept needs more than one line, that's
a sign it belongs in Detailed Notes instead.

## Detailed Notes
The real substance. Organized the way the video flows, with ## sub-headings
for each major beat. Use the timestamps the chunk summaries flagged — they
let the reader jump back to the exact moment in the video. Be generous here;
this is the section students will re-read the most.

Write in paragraphs where paragraphs work, bullets where bullets work.
Mix it up. Avoid the "Introduction:", "Definition:", "Example:" pattern that
makes notes feel like a fill-in-the-blank worksheet.

## Examples
The concrete examples the speaker used to make ideas land. A bulleted list
is fine. Skip this section if the video is mostly abstract and didn't lean
on examples.

## Key Takeaways
What the student should walk away remembering. Five to eight bullets.
These are the things that should still be true in their head a week from now.

## Revision Notes
The page they'd flip through the morning of an exam. Dense, short, no
narrative. Just the load-bearing facts and the must-remember formulas,
arranged so a tired brain can scan it in five minutes.

## Potential Interview Questions
Five to ten questions an interviewer might reasonably ask about this
material, with short answer sketches. Calibrate to the level of the
content — a 101 lecture gets gentler questions, a graduate seminar gets
harder ones. The questions should feel like things a curious interviewer
would actually ask, not a multiple-choice bank.

## Practice Questions
Five to ten exercises for the student to test their understanding. Vary the
difficulty. Some should be doable from memory, some should require real
thinking. Include the answer sketches at the bottom of the list, separated
by a blank line, so the student can try first and check later.

A few ground rules:
- Stay inside what the chunk summaries and transcript actually say. If the
  speaker was vague, the notes can be vague too — say "the speaker isn't
  fully precise here, but the gist is X" rather than making something up.
- If a section doesn't apply, just skip it. Don't write "N/A". Don't write
  a placeholder. Silence is fine.
- The first line of your output should be a Markdown header. No preamble.
  No "Here are the notes you requested." No closing pleasantries.
- Vary your phrasing. Don't start every bullet with "The speaker explains…"
  or "Students should know that…". Mix it up. Write like a person."""


def _assemble_lesson(
    title: str,
    chunk_summaries: Iterable[str],
    transcript: str,
    full_transcript_chars: int,
    progress_cb=None,
) -> str:
    """REDUCE step: combine chunk summaries into the final lesson notes."""
    if progress_cb:
        progress_cb("Assembling final lesson…", 92)

    model = _get_model()
    summaries_block = "\n\n---\n\n".join(chunk_summaries)

    # Keep the full transcript in the prompt, but only the first N characters
    # to avoid runaway size. The chunk summaries already carry the structure.
    transcript_budget = 20_000
    transcript_excerpt = transcript[:transcript_budget]
    if full_transcript_chars > transcript_budget:
        transcript_excerpt += (
            f"\n\n[…{full_transcript_chars - transcript_budget} more characters "
            "of transcript elided; rely on the chunk summaries above for full coverage]"
        )

    prompt = (
        f"{LESSON_NOTES_PROMPT}\n\n"
        f"Lesson title: {title}\n\n"
        f"Here are the chunk summaries ({sum(1 for _ in chunk_summaries)} of them, in order):\n\n"
        f"{summaries_block}\n\n"
        f"And here's a slice of the full transcript in case you need to grab a"
        f" specific phrase or number:\n```\n{transcript_excerpt}\n```"
    )

    resp = model.generate_content(prompt)
    if progress_cb:
        progress_cb("Assembling final lesson…", 95)
    return (resp.text or "").strip()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

# Default chunk sizing — 1100 tokens per chunk puts us comfortably under
# Gemini 2.5 Flash's 1M-token window while still being small enough that each
# chunk's summary easily fits in the reduce prompt.
DEFAULT_CHUNK_TOKENS = 1100
DEFAULT_OVERLAP_TOKENS = 150
MAX_CHUNKS_FOR_FALLBACK = 60


def generate_lesson_notes(
    transcript: str,
    title: str,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    progress_cb=None,
) -> str:
    """Generate structured lesson notes from a (potentially very long) transcript.

    Strategy:
      * Short transcripts (≤ chunk_tokens): single Gemini call (no chunking).
      * Long transcripts: map-reduce over chunk summaries.

    `progress_cb(message: str, pct: int)` is called periodically so the caller
    can show live progress to the user.
    """
    if not transcript or not transcript.strip():
        return ""

    total_tokens = estimate_tokens(transcript)
    logger.info(
        "generate_lesson_notes: %s — ~%d tokens, chunk=%d, overlap=%d",
        title, total_tokens, chunk_tokens, overlap_tokens,
    )

    # Short transcript: skip the map-reduce overhead.
    if total_tokens <= chunk_tokens:
        logger.info("Short transcript — using single-pass generation")
        if progress_cb:
            progress_cb("Generating notes (single pass)…", 80)
        return _assemble_lesson(
            title,
            chunk_summaries=[f"## Full transcript\n```\n{transcript}\n```"],
            transcript=transcript,
            full_transcript_chars=len(transcript),
            progress_cb=progress_cb,
        )

    # Long transcript: chunk, then map-reduce.
    chunks = chunk_transcript(
        transcript,
        chunk_tokens=chunk_tokens,
        overlap_tokens=overlap_tokens,
    )
    logger.info("Split into %d chunks", len(chunks))

    # Defensive cap — if a transcript is absurdly long, sample chunks evenly
    # to keep total work bounded.
    if len(chunks) > MAX_CHUNKS_FOR_FALLBACK:
        step = len(chunks) / MAX_CHUNKS_FOR_FALLBACK
        indices = [int(i * step) for i in range(MAX_CHUNKS_FOR_FALLBACK)]
        sampled = [chunks[i] for i in indices]
        logger.warning(
            "Transcript is very long (%d chunks); sampled down to %d",
            len(chunks), len(sampled),
        )
        chunks = sampled

    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks):
        logger.info("Summarizing chunk %d/%d (≈%d tokens)", i + 1, len(chunks), estimate_tokens(chunk))
        chunk_summaries.append(
            _summarize_chunk(chunk, i, len(chunks), title, progress_cb=progress_cb)
        )

    return _assemble_lesson(
        title,
        chunk_summaries=chunk_summaries,
        transcript=transcript,
        full_transcript_chars=len(transcript),
        progress_cb=progress_cb,
    )


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """You're a tutor helping a student work through a video they just watched.
The transcript excerpts below are your source material — treat them as the
textbook. You can quote, paraphrase, and point to specific moments, but
nothing else. If the answer isn't in those excerpts, say so plainly.

Voice and style:
- Write the way a good TA would talk in office hours. Warm, direct, not
  stiff. Contractions are fine. So are short sentences.
- Lead with the answer. Don't make the student wade through three
  sentences of throat-clearing before you get to the point.
- If the student asks for a summary, a quiz, flashcards, or a chapter
  walkthrough, give it to them in clean Markdown. No "Sure! Here's a
  summary:" preamble — just the content.
- Cite timestamps inline when you're pointing at a specific moment
  (e.g. "the speaker actually works through this around [00:12:34]"). It
  helps the student jump back to the video.
- When you don't know, say so. "The transcript doesn't really cover that
  — the closest thing is at [00:25:10] where the speaker says X" is
  better than guessing.
- Vary your sentence openings. Don't start every paragraph with "The
  video…" or "The speaker…". Mix it up. If you catch yourself writing
  the same phrase twice in a row, rewrite one of them.

Length:
- For a simple factual question, a sentence or two is plenty. Don't pad.
- For "explain X" or "walk me through Y", take the room you need but
  stop when you've said it. A 400-word answer to a 50-word question is
  a bad answer.
- For "make me a quiz" or "give me flashcards", the format speaks for
  itself. Don't add a paragraph explaining what you just did.

The excerpts are below."""


def chat_with_context(question: str, context_chunks: list[str]) -> str:
    """Answer a question using retrieved transcript chunks as context."""
    model = _get_model()

    context_block = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no context)"

    # Gemini doesn't have a "system" role in the same way; fold the system prompt
    # into the first user turn. We don't add a closing "Answer in Markdown" line
    # — if the student asks a casual question, a Markdown wall feels weird.
    prompt = (
        f"{CHAT_SYSTEM_PROMPT}\n\n"
        f"--- TRANSCRIPT EXCERPTS ---\n"
        f"{context_block}\n"
        f"--- END EXCERPTS ---\n\n"
        f"Student's question: {question}"
    )
    response = model.generate_content(prompt)
    return response.text or ""
