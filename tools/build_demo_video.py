"""Create a captioned five-minute walkthrough from actual captured UI screenshots.

Authoring dependencies: Pillow and imageio-ffmpeg==0.6.0. No browser automation.
"""

import hashlib
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/demo"
FONT = Path("C:/Windows/Fonts/arial.ttf")
BOLD = Path("C:/Windows/Fonts/arialbd.ttf")


def main():
    slides = [
        (
            "HLD Navigator | recorded walkthrough",
            None,
            "Sai Chakrith Sulluru | Amrita Viswa Vidyapeetham\nFaculty guide: Dr. D. Palmani\n\n"
            "Five-minute captioned walkthrough built from actual local UI captures.\n"
            "This is a prerecorded sequence of screenshots, not a continuous live recording.\n"
            "Fictional powertrain fixtures are used; Codex assistance is disclosed.",
        ),
        (
            "1. Upload and extract",
            "00-upload.png",
            "A real browser upload of torque-prose.md produced eight proposals.\n"
            "Original file bytes, SHA-256 and source locations are retained.\n"
            "Extraction creates proposals; it does not grant architecture approval.",
        ),
        (
            "2. Review source-linked proposals",
            "01-review.png",
            "Select a revision and inspect the Engine component's literal source statement.\n"
            "Fictional seeded v1/v2 facts are auto-approved only to demonstrate the workflow.\n"
            "This is not an independent engineering sign-off.",
        ),
        (
            "3. Preserve provenance and oversight",
            "01-review.png",
            "Each proposal links to a particular source occurrence, section and line.\n"
            "Source approval, fact decisions and warning resolution are separate controls.\n"
            "Reviewers can correct or reject facts while preserving original evidence.",
        ),
        (
            "4. Retrieve cited evidence",
            "02-search.png",
            "TorqueInterface search returns approved facts scoped to the chosen revision.\n"
            "The default output is lexical source excerpts with resolvable citations.\n"
            "Optional model synthesis has separate citation and semantic checks.",
        ),
        (
            "5. Build the reviewed architecture report",
            "03-report.png",
            "The dependency map shows ABS to Engine to Cluster using declared interfaces.\n"
            "Component reports include ports, incoming/outgoing edges and source citations.\n"
            "The exported inventory is scoped; it is not proof of document completeness.",
        ),
        (
            "6. Compare revisions",
            "04-compare.png",
            "The captured v1/v2 comparison reports two changed port records.\n"
            "Direction and data-type changes can trigger candidate architecture findings.\n"
            "Full cited before/after impact paths remain available, limited to two hops.",
        ),
        (
            "7. Demonstrate a review blocker",
            "05-blocker.png",
            "The public KUKSA source remains unreviewed. Export returns HTTP 409.\n"
            "Warnings and missing facts must be reviewed rather than waived silently.\n"
            "Public source provenance and licenses are included with the input corpus.",
        ),
        (
            "8. Verification and practical limits",
            None,
            "499 regression tests passed, with one upstream deprecation warning.\n"
            "Real HTTP, browser workflow, BGE embeddings and Tesseract OCR were exercised.\n\n"
            "Final Qwen 7B: 29/30 raw contract passes, 8/8 correct must-abstentions.\n"
            "Developer review: 8/12 useful complete answers; 3/5 conflict cases;\n"
            "4/5 safe useful injection answers, zero instruction-following in five cases.\n\n"
            "These synthetic cases do not establish OEM reliability or productivity gains.",
        ),
        (
            "9. Reproduce and explain the project",
            None,
            "Run: uv sync --frozen --extra dev\n"
            "Run: uv run python tools/demo.py\n"
            "Open: http://127.0.0.1:8511\n"
            "Enter the private terminal token with workspace demo and API port 8011.\n\n"
            "Read docs/INTERVIEW_DEMO.md and practice explaining extraction, provenance,\n"
            "retrieval, access control, revision analysis and recovery.\n"
            "Supply register/team ID and personal signatures before final submission.",
        ),
    ]
    frames = OUT / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    title_font = ImageFont.truetype(str(BOLD), 43)
    body_font = ImageFont.truetype(str(FONT), 30)
    card_font = ImageFont.truetype(str(FONT), 37)
    small_font = ImageFont.truetype(str(FONT), 23)
    paths = []
    for i, (title, screenshot, caption) in enumerate(slides):
        image = Image.new("RGB", (1920, 1080), "#F8FAFC")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1920, 90), fill="#193653")
        draw.text((48, 20), title, font=title_font, fill="white")
        if screenshot:
            capture = Image.open(OUT / "screenshots" / screenshot).convert("RGB")
            capture.thumbnail((1422, 800), Image.Resampling.LANCZOS)
            image.paste(capture, ((1920 - capture.width) // 2, 105))
            draw.multiline_text((48, 920), caption, font=body_font, fill="#193653", spacing=8)
        else:
            draw.multiline_text((80, 210), caption, font=card_font, fill="#193653", spacing=23)
        draw.text(
            (48, 1050),
            "Prerecorded UI captures | Synthetic demo | Codex assistance disclosed",
            font=small_font,
            fill="#516274",
        )
        draw.text((1760, 1050), f"{i + 1}/10", font=small_font, fill="#516274")
        target = frames / f"step-{i:02}.png"
        image.save(target)
        paths.append(target)
    listing = frames / "sequence.txt"
    listing.write_text(
        "".join(f"file '{p.as_posix()}'\nduration 30\n" for p in paths)
        + f"file '{paths[-1].as_posix()}'\n",
        encoding="utf-8",
    )
    output = OUT / "HLD_Navigator_Walkthrough_v1.1.mp4"
    executable = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            executable,
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-t",
            "301",
            "-vf",
            "tpad=stop_mode=clone:stop_duration=1",
            "-r",
            "24",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "2",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )
    receipt = {
        "file": output.name,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "duration_seconds_target": 301,
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "presentation": (
            "Captioned sequence of actual UI screenshots; no continuous capture or voice"
        ),
        "source_screenshots": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (OUT / "screenshots").glob("*.png")
        },
        "limitations": "Synthetic fixtures and developer validation; not an independent OEM demo",
    }
    (OUT / "video-provenance.json").write_text(json.dumps(receipt, indent=2))
    print(output)


if __name__ == "__main__":
    main()
