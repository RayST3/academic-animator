# Agent Handoff — Academic Animator

> Context file for an AI agent continuing this work. Read this first, then
> `README.md` (human-facing setup) and `animator.py` (the implementation).

## What this is

A self-contained [Agno](https://docs.agno.com) agent (`animator.py`) that takes
a topic or a PDF and renders a **narrated Manim animation** explaining it.
Backend: **Gemini 4 Hydrogen** (`agno.models.google.Gemini`, model id
`gemini-4-hydrogen`) with Agno fallbacks through Gemini 3.8 Flash, Gemini 3.6
Flash, Gemini 3.5 Flash Lite, Gemini 3.1 Flash Lite, and Gemma 4 31B IT.
Narration: **gTTS** via `manim-voiceover` (no API key for the voice; only the
Google model backend needs a key).

The demo reads whatever PDF is in `paper/` and produces a ~3-minute narrated
explainer of it. The prompt in `__main__` is **paper-agnostic** ("read the
attached paper, state what it's about, walk its core ideas in order with
visuals, close with the takeaway"), so the bundle works for any paper. The
example PDF currently shipped is `paper/2606.12683v1.pdf` (arXiv 2606.12683,
"From AGI to ASI"). `_find_paper()` discovers the PDF: if exactly one is in
`paper/` it's used automatically; if several, the user gets a numbered menu.

## Origin

Extracted from a larger project (`flash3.5teacher`, an AgentOS "teacher" Team
with animator/coder/judge members). This bundle is a **standalone copy** of just
the animator + its Manim toolkit + the example paper, repackaged so it can be
zipped and shared.

## File map

```
academic-animator/
├── animator.py          # the agent; __main__ runs the bundled-paper demo
├── tools/manim_tools.py # Manim render toolkit (Toolkit subclass; render_scene)
├── paper/...pdf         # example input
├── requirements.txt     # pinned, verified versions
├── .env.example         # copy -> .env, add GOOGLE_API_KEY
├── README.md            # human setup/run/config/troubleshooting
└── AGENT_CONTEXT.md     # this file
```

Runtime artifacts (gitignore-worthy, safe to delete): `animator.db`, `tmp/manim/`.

## Key decisions & history (why things are the way they are)

1. **Self-sufficient, not a factory.** The original `animator.py` used a
   `build_animator_agent(db, dir)` factory injected by the parent app. The user
   explicitly wanted a standalone module: it builds its own `Gemini` model,
   `SqliteDb`, and `ManimTools`, calls `load_dotenv()`, and has a runnable
   `__main__`. Do **not** reintroduce the factory pattern here.

2. **Duration / timeout.** `max_duration_seconds=600.0` (10-min cap, was 20s),
   `timeout_seconds=1800` (30 min) so a 3-min narrated render isn't killed.

3. **Voiceover via gTTS.** `enable_voiceover=True, voice_service="gtts"`. The
   toolkit auto-injects VoiceoverScene instructions. Agent instructions were
   rewritten from "keep scenes under 10s" to "target the requested length,
   ~380–450 words narration across 8–14 voiceover beats."

4. **PDF is sent natively.** `__main__` attaches the real PDF via
   `agno.media.File(filepath=...)` (Gemini reads PDFs natively) — NOT a
   hand-written text summary. User insisted on passing the actual paper.

5. **LaTeX is avoided on purpose.** Renders failed on Windows with
   `FileNotFoundError: [WinError 2]` because the model used `MathTex`/`Tex`,
   which shell out to `latex` (not installed). We diagnosed it (latex/dvisvgm/
   xelatex all missing; SoX + ffmpeg present). User chose NOT to install LaTeX
   to save C: space. Fix: an instruction forbidding `Tex`/`MathTex` and forcing
   Pango `Text`/`MarkupText` with Unicode math (`ℏω`, `Δ`, `2.1 eV`). If you
   ever want real math typesetting, install MiKTeX (portable, D: drive) and
   relax that instruction.

6. **`delete_after_render=False`.** Default toolkit behavior inlines any render
   ≤ 25 MB into the response as base64 and DELETES the file — that's why the
   first successful video "couldn't be found." Now files are kept on disk.

7. **Quality.** Toolkit default is `quality="m"` (720p30) but the model passes a
   per-call `quality="h"` override, so output came out **1080p60** (confirmed via
   folder name `1080p60` + ffprobe 1920x1080@60). To pin it, either instruct the
   model not to pass `quality`, or hard-pin in `manim_tools.py`
   (`q = self.default_quality`). Currently left as-is (user OK with 1080p60).

## Verified working state

A successful run (on an earlier example paper) produced an mp4 of **2:49**,
**1920x1080 @ 60fps**, stereo 48kHz audio, **8.27 MB**, with sibling `.srt`
captions and `.wav` narration. Pipeline is confirmed end-to-end.

## Environment notes (the machine this was built on — Windows 11)

- venv: `D:\programs\phidata\aienv` (Python 3.12). Verified versions:
  `agno==2.6.18`, `google-genai==2.5.0`, `manim==0.20.1`,
  `manim-voiceover==0.4.0`, `gTTS==2.5.4`, `python-dotenv==1.2.2`.
- `ffmpeg`/`ffprobe`: present (winget Gyan.FFmpeg). **Required.**
- `sox`: present (winget ChrisBagwell.SoX 14.4.2). Only used if narration speed
  is changed (`global_speed != 1`); not on the default path.
- LaTeX: **absent by design.**
- Windows pip gotcha: installing `manim-voiceover` tried to upgrade pip itself
  and failed; fix is `python -m pip install ...` (not bare `pip`).

## Toolkit cheatsheet (`tools/manim_tools.py`)

- Class `ManimTools(Toolkit)`. Main tool: `render_scene(scene_code, scene_name,
  quality=None)` → writes a temp `.py`, runs `python -m manim -<flag> ...`,
  locates the mp4, probes duration, enforces `max_duration_seconds`, and returns
  a `ToolResult` with the `Video` attached. `quality` map:
  `l`=480p15, `m`=720p30, `h`=1080p60, `k`=2160p60.
- It's vendored from an unmerged agno PR (see the module docstring). If you
  upgrade agno and `ManimTools` ships upstream, consider switching to the
  official `agno.tools.manim`.

## Open / possible next steps

- (Optional) Pin render quality to avoid the model's `h` override.
- (Optional) Add a `.gitignore`-equivalent note or strip `tmp/` before zipping.
- (Optional) Parameterize the `__main__` prompt / paper path via CLI args so the
  team can point it at other papers without editing code.
- (Optional) Ship a pre-rendered sample mp4 in the bundle (not currently
  included).
- If multilingual or higher-quality narration is needed, swap `voice_service`
  to `openai`/`elevenlabs` (needs the respective API key + extra install).
