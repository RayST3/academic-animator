# Frontend — Academic Animator (chat UI)

A lightweight **chat app** ([Gradio](https://www.gradio.app/)) wired to the
`animator` agent. Send a message and/or attach files (PDFs, images, text); the
agent runs through agno's built-in `.run()` and replies in the chat. When it
renders a Manim video, the video plays inline.

Each conversation has its own UUID-backed Agno session, so follow-up messages
build on the selected conversation without mixing it with other demos. Saved
conversations appear in the sidebar and can be reopened or deleted.

---

## Setup (Windows / PowerShell)

Run these from the **project root** (`academic-animator/`), not from this
folder, so the API key and imports resolve cleanly.

```powershell
# 0. install uv if you don't have it (either works)
pip install uv
#    or:  winget install astral-sh.uv  (then open a new terminal)

# 1. create + activate a virtual environment
uv venv .venv
.venv\Scripts\Activate.ps1
#    (If PowerShell blocks the script:
#     Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#     or use:  .venv\Scripts\activate.bat)

# 2. install the frontend's dependencies (full stack incl. the animator)
uv pip install -r frontend\requirements.txt

# 3. add your Gemini API key (if you haven't already)
#    copy .env.example -> .env in the project root and paste your key
copy .env.example .env
```

`.env` (in the project root):
```
GOOGLE_API_KEY=AIza...your-key...
```

You also need **FFmpeg** on PATH (`winget install Gyan.FFmpeg`) — see the main
[`../README.md`](../README.md#prerequisites) for details.

---

## Run

```powershell
python frontend\app.py
```

Open the URL it prints (default http://127.0.0.1:7860). Type a request like
*"Explain how binary search works in about a minute"*, or attach a PDF and ask
for a narrated explainer. Renders take a few minutes; keep the tab open.

To expose it on your network (e.g. for teammates on the same LAN), edit the
`demo.queue().launch()` line in `app.py` to
`demo.queue().launch(server_name="0.0.0.0")`.

---

## How it works

- `app.py` adds the project root to `sys.path` and does `from animator import
  animator` — it reuses the exact same agent the CLI uses, so model, tools,
  voiceover, and quality settings all match.
- The **New conversation** button generates a UUID. That UUID is passed as the
  Agno `session_id`, isolating its database history from every other chat.
- Saved Agno sessions are listed in the sidebar. Selecting one loads its runs
  and persisted video file paths from SQLite; the first prompt becomes its
  display title. Gradio streams each file by path rather than embedding the
  video bytes in the database or model context.
- Uploaded files are sorted into agno `Image` / `File` media and passed to
  `animator.run(...)`. Text-only messages just run as a prompt.
- After the run, the newest `.mp4` under `../tmp/manim/` is shown in the chat.
  The renderer returns only its save path to the model; video bytes are never
  sent back as model input.

## Troubleshooting

- **Auth error / empty reply** — `GOOGLE_API_KEY` missing/invalid in the project
  root `.env`.
- **`FileNotFoundError` during render** — FFmpeg isn't on PATH (install it). The
  agent is kept off LaTeX by design.
- **No video appears** — the render may have failed; the agent's text reply in
  the chat explains what happened. Check the terminal for the Manim stderr.
