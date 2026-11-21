# 🚨 SECRET PROJECT — DELETE THIS ENTIRE BUNDLE THE DAY BEFORE THE EVENT.
# Remove the whole academic-animator/ folder (and any copies/zips) from every
# machine the day before the event. Do not redistribute.

"""Chat frontend for the Academic Animator.

A regular chat app (Gradio) wired to the `animator` agent. Type a message and/or
attach PDFs / images / other files; the agent runs via agno's built-in `.run()`
and replies in the chat. When it renders a Manim video, the video plays inline.

Run it from the project root:

    python frontend/app.py

then open the printed URL (default http://127.0.0.1:7860).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import gradio as gr

# Make the parent project importable so `from animator import ...` works no
# matter where this script is launched from.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agno.media import File, Image  # noqa: E402

# Importing the agent also builds its model/db/tools and calls load_dotenv().
from animator import animator, MANIM_OUTPUT_DIR  # noqa: E402

# One stable session id => agno keeps the conversation history across messages
# (the agent already has add_history_to_context=True).
SESSION_ID = "frontend-chat"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

# Default instruction applied when files are attached without any text.
DEFAULT_PROMPT = (
    "Read the attached file(s) and make a ~3 minute narrated Manim video that "
    "explains the material for a curious student: open by stating what it's "
    "about, walk through the core ideas in order with clear visuals, and close "
    "with the main takeaway. Render it once."
)


def _newest_mp4(after_ts: float) -> Path | None:
    """Newest .mp4 written under the manim output dir since `after_ts`.

    The agent keeps renders on disk (delete_after_render=False), so the freshest
    mp4 produced during this run is the one we just made.
    """
    vids = [p for p in MANIM_OUTPUT_DIR.rglob("*.mp4") if p.stat().st_mtime >= after_ts]
    return max(vids, key=lambda p: p.stat().st_mtime) if vids else None


def _split_attachments(paths: list[str]) -> tuple[list[Image], list[File]]:
    """Sort uploaded files into agno Image / File media objects."""
    images, files = [], []
    for p in paths:
        if Path(p).suffix.lower() in IMAGE_EXTS:
            images.append(Image(filepath=p))
        else:
            files.append(File(filepath=p))
    return images, files


def chat(message: dict, history: list) -> list:
    """Gradio ChatInterface handler (multimodal, type='messages').

    `message` is {"text": str, "files": [paths]}. Yields assistant message(s).
    """
    text = (message.get("text") or "").strip()
    paths = message.get("files") or []
    if not text and not paths:
        yield gr.ChatMessage(role="assistant", content="Type a message or attach a file.")
        return

    yield gr.ChatMessage(
        role="assistant",
        content="⏳ Working on it… a render can take a few minutes. Hang tight.",
    )

    images, files = _split_attachments(paths)
    prompt = text or DEFAULT_PROMPT
    start = time.time()
    try:
        response = animator.run(
            prompt,
            images=images or None,
            files=files or None,
            session_id=SESSION_ID,
        )
    except Exception as exc:  # show the failure in the chat, not just the console
        yield gr.ChatMessage(role="assistant", content=f"❌ Generation failed: {exc}")
        return

    caption = (getattr(response, "content", "") or "").strip()
    video = _newest_mp4(start)

    out: list = []
    if caption:
        out.append(gr.ChatMessage(role="assistant", content=caption))
    if video is not None:
        out.append(gr.ChatMessage(role="assistant", content=gr.Video(str(video))))
    if not out:
        out.append(
            gr.ChatMessage(
                role="assistant",
                content="Done — but no video was found under `tmp/manim/`.",
            )
        )
    yield out


demo = gr.ChatInterface(
    fn=chat,
    type="messages",
    multimodal=True,
    title="🎬 Academic Animator",
    description=(
        "Chat with the animator. Ask for a video on any topic, or attach a PDF "
        "(or images) to turn into a narrated Manim animation. "
        "🚨 _Secret project — delete this bundle the day before the event._"
    ),
    textbox=gr.MultimodalTextbox(
        file_types=[".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md"],
        placeholder="Ask for an animation, or attach a PDF…",
    ),
)


if __name__ == "__main__":
    # queue() so a multi-minute render doesn't time out the request.
    demo.queue().launch()
