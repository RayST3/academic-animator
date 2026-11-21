# 🚨 SECRET PROJECT — DELETE THIS ENTIRE BUNDLE THE DAY BEFORE THE EVENT.
# Remove the whole academic-animator/ folder (and any copies/zips) from every
# machine the day before the event. Do not redistribute.

"""Animator — a self-contained Agno agent that writes a Manim Scene subclass
and renders it into a narrated mp4.

Powered by Gemini 3.5 Flash. The agent is fully self-sufficient: it builds its
own model, database, and Manim tooling, so you can either import `animator`
from this module or run it directly:

    python animator.py

Running it directly reads whatever PDF you drop in `paper/` and renders a
~3 minute narrated explainer of it. Output lands in `tmp/manim/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

# Make this folder importable so `tools` resolves when run from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.media import File
from agno.models.google import Gemini

from tools.manim_tools import ManimTools

load_dotenv()

MODEL_ID = "gemini-3.5-flash"

DB_FILE = PROJECT_ROOT / "tmp" / "animator.db"
MANIM_OUTPUT_DIR = PROJECT_ROOT / "tmp" / "manim"
MANIM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

animator = Agent(
    id="animator",
    name="Animator",
    role="Manim animator. Writes a Manim Community Edition Scene subclass "
    "and renders it into an mp4. Use for any concept that benefits "
    "from a visual: math (limits, derivatives, integrals, linear algebra), "
    "CS (sorting, traversal, recursion), engineering (forces, circuits, "
    "waves), physics. The video is attached to the response automatically.",
    model=Gemini(id=MODEL_ID),
    debug_mode=True,
    db=SqliteDb(db_file=str(DB_FILE)),
    tools=[
        ManimTools(
            output_dir=MANIM_OUTPUT_DIR,
            timeout_seconds=1800,
            max_duration_seconds=600.0,
            quality="m",
            enable_voiceover=True,
            voice_service="gtts",
            delete_after_render=False,
        )
    ],
    instructions=[
        "You are an expert in Manim Community Edition. You write Scene "
        "subclasses in Python and render them into narrated animation videos.",
        "Voiceover is ENABLED via gTTS. Subclass `VoiceoverScene` (not "
        "`Scene`), set the speech service at the top of `construct`, and wrap "
        "every visual beat in `with self.voiceover(text=...) as tracker:` "
        "using `run_time=tracker.duration` so the animation length matches the "
        "narration. The narration is what sets the video's pace and length.",
        "Compose a single Python string starting with `from manim import *` "
        "(plus the voiceover imports) and a class whose name matches the "
        "`scene_name` argument you pass to `render_scene`.",
        "Match the video length the student asks for. For a ~3 minute video, "
        "write roughly 380-450 words of narration spread across 8-14 "
        "`self.voiceover(...)` beats, each its own visual section. Let "
        "`run_time=tracker.duration` (and short `self.wait(...)` only where "
        "needed) drive the timing rather than padding with fixed waits.",
        "Always call `render_scene(scene_code=..., scene_name=...)` exactly "
        "once with the full source. Do not split the code across multiple "
        "tool calls.",
        "If a render fails, read the stderr tail carefully, fix the scene "
        "code, and retry once. If it fails again, explain the failure to "
        "the student in plain English.",
        "After a successful render, write a 1-3 sentence caption explaining "
        "what the animation shows. The video will be displayed inline by "
        "the frontend.",
        "Prefer dark backgrounds and bold colors (BLUE, TEAL, YELLOW).",
        "LaTeX is NOT installed, so AVOID `Tex`, `MathTex`, and any LaTeX-backed "
        "mobject — they shell out to `latex` and the render crashes with a "
        "FileNotFoundError. Use `Text(...)` and `MarkupText(...)` (Pango-based) "
        "for ALL labels, and write maths with plain Unicode (e.g. 'ℏω', 'Δ', "
        "'λ', '2.1 eV', 'E = ℏω'). Only reach for MathTex if a formula is truly "
        "impossible in Unicode, and expect it to fail without LaTeX.",
    ],
    add_history_to_context=True,
    num_history_runs=2,
    markdown=True,
)


PAPER_DIR = PROJECT_ROOT / "paper"


def _find_paper() -> Path:
    """Return the PDF to animate from the `paper/` folder.

    Drop your own paper into `paper/` and it is picked up automatically. If
    several PDFs are present, you're shown a menu to choose which one to use.
    """
    pdfs = sorted(PAPER_DIR.glob("*.pdf"))
    if not pdfs:
        sys.exit(
            f"No PDF found in {PAPER_DIR}. Drop a .pdf into the 'paper/' "
            "folder (or pass your own via the `files=[File(...)]` argument)."
        )
    if len(pdfs) == 1:
        return pdfs[0]

    print(f"\nMultiple PDFs found in {PAPER_DIR.name}/ — pick one to animate:\n")
    for i, pdf in enumerate(pdfs, start=1):
        print(f"  {i}. {pdf.name}")
    while True:
        choice = input(f"\nEnter a number (1-{len(pdfs)}, default 1): ").strip()
        if not choice:
            return pdfs[0]
        if choice.isdigit() and 1 <= int(choice) <= len(pdfs):
            return pdfs[int(choice) - 1]
        print("  Invalid choice, try again.")


if __name__ == "__main__":
    paper_pdf = _find_paper()
    print(f"\nAnimating: {paper_pdf.name}\n")
    animator.print_response(
        "Read the attached research paper and make a ~3 minute narrated Manim "
        "video that explains it for a curious student. Open by stating what the "
        "paper is about, then walk through its core ideas in a logical order, "
        "using clear visuals (diagrams, labelled shapes, simple plots/timelines) "
        "for each key concept, and close with the main takeaway. Keep the "
        "narration accessible and render it once.",
        files=[File(filepath=paper_pdf)],
        stream=True,
    )
