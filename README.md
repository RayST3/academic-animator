# Academic Animator (Secret Project)

A self-contained [Agno](https://docs.agno.com) agent that reads a topic (or a
PDF) and renders a **narrated Manim animation** explaining it. Powered by
Gemini 3.5 Flash, with voiceover via gTTS.

Out of the box, running it reads the example paper bundled in `paper/` and
produces a ~3-minute narrated explainer of it. Swap in your own PDF anytime
(see [Use your own paper](#use-your-own-paper)).

> ⚠️ Confidential — secret internal project. Do not redistribute.
>
> 🚨 **DELETE THIS ENTIRE BUNDLE THE DAY BEFORE THE EVENT.** Remove the whole
> `academic-animator/` folder (and any copies/zips) from every machine the day
> before the event.

---

## What's in this folder

```
academic-animator/
├── animator.py            # the agent + a runnable __main__ demo
├── tools/
│   └── manim_tools.py     # Manim render toolkit (writes a Scene, renders to mp4)
├── paper/
│   └── 2606.12683v1.pdf     # example input paper — drop your own PDF here
├── requirements.txt       # pinned Python dependencies
├── .env.example           # copy to .env and add your GOOGLE_API_KEY
├── README.md
└── AGENT_CONTEXT.md       # handoff/context summary for an AI agent continuing the work
```

Generated at runtime (safe to delete):
- `animator.db`  — Agno session store (SQLite)
- `tmp/manim/`   — rendered `.mp4`, `.srt` captions, `.wav` audio, scratch files

---

## Prerequisites

> Setup below targets **Windows** (the team is all Windows). Commands assume
> PowerShell.

1. **Python 3.10–3.12**
2. **FFmpeg** on your PATH (`ffmpeg` and `ffprobe`) — Manim needs it to encode
   video and probe duration.
   - `winget install Gyan.FFmpeg`
   - After installing, open a **new** terminal so the updated PATH is picked up,
     then verify with `ffmpeg -version` and `ffprobe -version`.
3. A **Gemini API key** (free tier works): https://aistudio.google.com/apikey

### Optional (only if you want them)
- **SoX** — only used if narration speed is changed (`global_speed != 1`).
  Not required for the default setup.
  - `winget install ChrisBagwell.SoX`
- **LaTeX** — **not required and intentionally avoided.** The agent is
  instructed to use Manim's Pango text (`Text` / `MarkupText`) with Unicode
  math instead of `Tex` / `MathTex`, so no TeX distribution is needed. If you
  *want* real LaTeX typesetting, install MiKTeX/TeX Live and relax that
  instruction in `animator.py`.

---

## Setup

This bundle uses [uv](https://docs.astral.sh/uv/) for the environment and
installs.

```powershell
# 0. install uv if you don't have it (either works)
pip install uv
#    or:  winget install astral-sh.uv
#    (with winget, open a NEW terminal afterwards so `uv` is on PATH)

# 1. create + activate a virtual environment
uv venv .venv
.venv\Scripts\Activate.ps1
#    (If PowerShell blocks the script, run:
#     Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
#     or use the cmd activator: .venv\Scripts\activate.bat)

# 2. install dependencies
uv pip install -r requirements.txt

# 3. add your API key
#    copy .env.example -> .env and paste your key
copy .env.example .env
```

`.env`:
```
GOOGLE_API_KEY=AIza...your-key...
```

---

## Run

Prefer a **chat UI**? See [`frontend/`](frontend/README.md) — a Gradio chat app
(text + file/PDF uploads) wired to the same agent. Otherwise, the CLI demo:

```powershell
python animator.py
```

This picks up the PDF in `paper/`, sends it to the agent, and asks for a
~3-minute narrated video. When it finishes, find the output under:

```
tmp/manim/media_<id>/videos/<SceneName>_<id>/<quality>/<SceneName>.mp4
```

A `.srt` (captions) and `.wav` (narration) are written alongside it.

---

## Use your own paper

The demo animates whatever PDF lives in the `paper/` folder — there's nothing
topic-specific hard-coded, so it works for any paper:

1. Drop your `.pdf` into `paper/`.
2. Run `python animator.py`.

If the folder has **one** PDF, it's used automatically. If it has **several**,
you'll get a numbered menu to choose which one to animate (press Enter for the
first). To use a different folder or path entirely, drive the agent from Python
(see below).

---

## Using it for your own topics

`animator` is a normal Agno `Agent`, so import and drive it however you like:

```python
from animator import animator
from agno.media import File

# plain prompt
animator.print_response("Make a 1-minute video explaining how a binary search works.")

# with your own PDF
animator.print_response(
    "Summarize this paper as a 2-minute narrated animation.",
    files=[File(filepath="path/to/your.pdf")],
)
```

---

## Configuration (in `animator.py`)

Inside the `ManimTools(...)` block:

| Param                   | Default | Meaning |
|-------------------------|---------|---------|
| `quality`               | `"m"`   | Render preset: `l`=480p15, `m`=720p30, `h`=1080p60, `k`=2160p60. **The model may override this per call** (it tends to pick `h`). |
| `max_duration_seconds`  | `600.0` | Hard cap (10 min). Longer renders are rejected so the agent shortens and retries. |
| `timeout_seconds`       | `1800`  | Kill the render subprocess after 30 min. |
| `enable_voiceover`      | `True`  | Narration on. |
| `voice_service`         | `"gtts"`| Free Google TTS, no API key. (Others: `openai`, `elevenlabs`, `azure`…) |
| `delete_after_render`   | `False` | Keep files on disk. Set `True` to inline small videos into the response and delete them. |

To force the resolution (the model otherwise overrides `quality`), add an
instruction telling it not to pass a `quality` argument, or hard-pin it in
`tools/manim_tools.py`.

---

## Troubleshooting

- **`FileNotFoundError: [WinError 2]` during render** — a binary the scene
  needs isn't on PATH. Almost always **LaTeX** (the scene used `MathTex`/`Tex`)
  or **FFmpeg**. Install FFmpeg; keep the agent off LaTeX (default).
- **`manim` import error** — `uv pip install -r requirements.txt` didn't run in
  the active environment (activate `.venv` first).
- **`uv` not found** — install it with `winget install astral-sh.uv`, then open a
  new terminal. (No uv? `python -m pip install -r requirements.txt` still works.)
- **No video found** — if you set `delete_after_render=True`, renders ≤ 25 MB
  are inlined into the response and deleted from disk. Keep it `False` to retain
  files.
- **Auth error / empty response** — `GOOGLE_API_KEY` missing or invalid in
  `.env`.
