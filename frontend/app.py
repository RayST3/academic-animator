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
import uuid
import re
from pathlib import Path

import gradio as gr

# Make the parent project importable so `from animator import ...` works no
# matter where this script is launched from.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agno.media import File, Image  # noqa: E402
from agno.db.base import SessionType  # noqa: E402

# Importing the agent also builds its model/db/tools and calls load_dotenv().
from animator import animator, MANIM_OUTPUT_DIR  # noqa: E402

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
MAX_SESSION_TITLE_LENGTH = 48

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


def _new_session_id() -> str:
    return str(uuid.uuid4())


def _get_sessions() -> list:
    return animator.db.get_sessions(
        session_type=SessionType.AGENT,
        component_id=animator.id,
        sort_by="updated_at",
        sort_order="desc",
        limit=100,
    )


def _session_title(session) -> str:
    session_data = session.session_data or {}
    title = session_data.get("session_name")
    if title:
        return str(title)

    for run in session.runs or []:
        prompt = (getattr(getattr(run, "input", None), "input_content", None) or "").strip()
        if prompt:
            return prompt[:MAX_SESSION_TITLE_LENGTH]

    return "Untitled conversation"


def _session_choices(active_session_id: str) -> list[tuple[str, str]]:
    choices = [(_session_title(session), session.session_id) for session in _get_sessions()]
    if not any(session_id == active_session_id for _, session_id in choices):
        choices.insert(0, ("New conversation", active_session_id))
    return choices


def _session_picker_update(active_session_id: str):
    return gr.update(
        choices=_session_choices(active_session_id),
        value=active_session_id,
    )


def _video_paths_from_messages(messages: list) -> list[Path]:
    video_paths = []
    for message in messages or []:
        content = getattr(message, "content", None)
        if not isinstance(content, str):
            continue
        match = re.search(
            r"The video was saved to (.+?); the generated media is not included",
            content,
        )
        if not match:
            continue

        path = Path(match.group(1))
        if path.exists() and path not in video_paths:
            video_paths.append(path)
    return video_paths


def _load_history(session_id: str) -> list[dict]:
    session = animator.db.get_session(session_id, SessionType.AGENT)
    if session is None:
        return []

    history = []
    for run in session.runs or []:
        prompt = (getattr(getattr(run, "input", None), "input_content", None) or "").strip()
        if prompt:
            history.append({"role": "user", "content": prompt})

        content = (getattr(run, "content", None) or "").strip()
        if content:
            history.append({"role": "assistant", "content": content})

        for video_path in _video_paths_from_messages(getattr(run, "messages", None)):
            history.append({"role": "assistant", "content": gr.Video(str(video_path))})
    return history


def _display_user_message(message: dict) -> str:
    text = (message.get("text") or "").strip()
    paths = [Path(path).name for path in (message.get("files") or [])]
    if not paths:
        return text

    attachments = ", ".join(f"`{path}`" for path in paths)
    return f"{text}\n\nAttachments: {attachments}" if text else f"Attachments: {attachments}"


def _name_session(session_id: str, message: dict) -> None:
    session = animator.db.get_session(session_id, SessionType.AGENT)
    if session is None or (session.session_data or {}).get("session_name"):
        return

    text = (message.get("text") or "").strip()
    paths = message.get("files") or []
    title = text or (f"Animation of {Path(paths[0]).name}" if paths else "New conversation")
    title = " ".join(title.split())[:MAX_SESSION_TITLE_LENGTH]
    animator.db.rename_session(session_id, SessionType.AGENT, title)


def start_session():
    session_id = _new_session_id()
    return session_id, [], _session_picker_update(session_id)


def new_session():
    return start_session()


def select_session(session_id: str):
    if not session_id:
        return start_session()
    return session_id, _load_history(session_id), _session_picker_update(session_id)


def refresh_sessions(session_id: str):
    return _session_picker_update(session_id)


def delete_session(session_id: str):
    if session_id and animator.db.get_session(session_id, SessionType.AGENT) is not None:
        animator.db.delete_session(session_id)
    return start_session()


def chat(message: dict, history: list, session_id: str):
    """Run one turn while keeping Agno history scoped to the active session.

    `message` is {"text": str, "files": [paths]}. Yields assistant message(s).
    """
    text = (message.get("text") or "").strip()
    paths = message.get("files") or []
    if not text and not paths:
        yield list(history or []), gr.update(value=None), _session_picker_update(session_id)
        return

    updated_history = list(history or [])
    updated_history.append({"role": "user", "content": _display_user_message(message)})
    updated_history.append(
        {
            "role": "assistant",
            "content": "⏳ Working on it… a render can take a few minutes. Hang tight.",
        }
    )
    yield updated_history, gr.update(value=None), _session_picker_update(session_id)

    images, files = _split_attachments(paths)
    prompt = text or DEFAULT_PROMPT
    start = time.time()
    try:
        response = animator.run(
            prompt,
            images=images or None,
            files=files or None,
            session_id=session_id,
        )
    except Exception as exc:  # show the failure in the chat, not just the console
        updated_history[-1] = {
            "role": "assistant",
            "content": f"❌ Generation failed: {exc}",
        }
        yield updated_history, gr.update(value=None), _session_picker_update(session_id)
        return

    _name_session(session_id, message)
    caption = (getattr(response, "content", "") or "").strip()
    videos = _video_paths_from_messages(getattr(response, "messages", None))
    if not videos:
        newest_video = _newest_mp4(start)
        if newest_video is not None:
            videos = [newest_video]

    updated_history[-1] = {
        "role": "assistant",
        "content": caption or "Done — but no text response was returned.",
    }
    for video in videos:
        updated_history.append(
            {"role": "assistant", "content": gr.Video(str(video))}
        )
    yield updated_history, gr.update(value=None), _session_picker_update(session_id)


with gr.Blocks(
    title="Academic Animator",
    fill_height=True,
    css="""
    #session-sidebar { min-width: 220px; }
    #session-sidebar .wrap { gap: 0.35rem; }
    """,
) as demo:
    active_session_id = gr.State()

    with gr.Row():
        with gr.Column(scale=1, min_width=220, elem_id="session-sidebar"):
            gr.Markdown("## Sessions")
            new_session_button = gr.Button("＋ New conversation", variant="primary")
            session_picker = gr.Radio(
                choices=[],
                value=None,
                label="Previous conversations",
                interactive=True,
                container=False,
            )
            with gr.Row():
                refresh_button = gr.Button("Refresh", size="sm")
                delete_button = gr.Button("Delete", size="sm")

        with gr.Column(scale=4):
            gr.Markdown("# 🎬 Academic Animator")
            gr.Markdown(
                "Chat with the animator. Ask for a video on any topic, or attach "
                "a PDF or images to turn into a narrated Manim animation."
            )
            chatbot = gr.Chatbot(
                type="messages",
                label="Conversation",
                height=600,
                show_copy_button=True,
                allow_tags=False,
            )
            message_box = gr.MultimodalTextbox(
                file_types=[".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md"],
                file_count="multiple",
                placeholder="Ask for an animation, or attach a PDF…",
                show_label=False,
                submit_btn=True,
                stop_btn=True,
            )

    session_state_outputs = [active_session_id, chatbot, session_picker]
    demo.load(
        fn=start_session,
        outputs=session_state_outputs,
    )
    new_session_button.click(
        fn=new_session,
        outputs=session_state_outputs,
    )
    session_picker.select(
        fn=select_session,
        inputs=session_picker,
        outputs=session_state_outputs,
    )
    refresh_button.click(
        fn=refresh_sessions,
        inputs=active_session_id,
        outputs=session_picker,
    )
    delete_button.click(
        fn=delete_session,
        inputs=active_session_id,
        outputs=session_state_outputs,
    )
    message_box.submit(
        fn=chat,
        inputs=[message_box, chatbot, active_session_id],
        outputs=[chatbot, message_box, session_picker],
    )


if __name__ == "__main__":
    # queue() so a multi-minute render doesn't time out the request.
    demo.queue().launch()
