# Superseded historical handoff

This describes v1.2 before the technical evaluation. See REMEDIATION_REPORT.md
for the current state. The project is not administratively eligible until the
mandatory live recording, personal declarations and faculty approval are supplied.

# Morning handoff - 09 October 2026

The software and reproducible interview demo are implemented. The portable
submission package is `output/submission/HLD_Navigator_Submission_v1.2.zip`.
It contains source/lockfile/tests, synthetic and public inputs/provenance,
model/prompt configuration, raw evaluation evidence, report, synopsis,
presentation, captioned walkthrough and unsigned declarations.

## Verified outcome

- 499 tests passed; lint passed. One upstream Starlette/httpx warning remains.
- Actual browser upload produced eight fictional proposals. Source citations,
  reviewed graph, revision changes and unreviewed-export HTTP 409 were observed.
- Backup/restore, workspace access and revocation are regression-tested.
- Qwen 7B weights and llama.cpp runtime were hash verified. The real API returned
  the correct uint16/Nm Torque answer with its exact source citation.
- Fixed 30-case final run: 29 raw contract passes, all eight must-abstentions,
  no instruction-following in five developer-reviewed injection cases. Useful
  complete answers: 8/12 answerable, 3/5 conflicts and 4/5 injections. Wrong
  recipient/revision recommendations remain semantic failures. Prior runs are kept.
- Real BGE retrieval matched lexical recall but had lower MRR on four questions.
- Real Tesseract 5.5.0 processed seven scanned instruction pages. This verifies
  integration, not OCR accuracy on automotive HLDs.
- Five pinned public KUKSA documents are included; the three-document baseline
  still contains parser omissions against provisional agent annotations.

The presentation is version 1.2; PDFs and the captioned video are version 1.1.
The video is a five-minute sequence of actual UI screenshots with explanatory
captions, without a voice track. It is explicitly prerecorded rather than a
continuous live capture. Practice the live walkthrough; replace or supplement
this backup with your own spoken recording if your evaluator requires it.

## Start when you return

```powershell
uv sync --frozen --extra dev
uv run python tools/demo.py
```

Open http://127.0.0.1:8511, set API http://127.0.0.1:8011 and workspace `demo`,
then enter the private terminal token. The default `.data/interview-demo.db`
has not been used for the recording. Choose a new `--database` path on later runs.
Ctrl+C stops the services; databases are retained. Read `docs/INTERVIEW_DEMO.md`.

For optional local models, follow `docs/s1b-local-answers.md`. Provisioning requires
network access; inference runs locally. Tesseract was installed to
`C:/Program Files/Tesseract-OCR/tesseract.exe` by the official installer; set
`HLD_NAVIGATOR_OCR=1` and `HLD_NAVIGATOR_TESSERACT` to that executable when needed.
Every OCR page requires review. No proprietary OEM HLD was supplied or fabricated.

## Personal submission steps

1. Supply your register/team ID and replace `ID_PENDING` in the package names.
2. Read and verify the artifacts, rewrite the study notes in your own words,
   and sign your integrity/AI-use declarations personally.
3. Obtain faculty approval/signature from Dr. D. Palmani where required.
4. Practice the ten-minute presentation, ten-minute live demo and technical Q&A.

Known identity: Sai Chakrith Sulluru; Amrita Viswa Vidyapeetham; Dr. D. Palmani.
The assistant reviewed its own implementation under your authorization. No
independent architect sign-off, protected OEM holdout, measured time saving,
safety/AUTOSAR certification or production deployment is claimed. Hosted CI is
configured but has not been observed running.

For applications, use `docs/PORTFOLIO.md` and the interview walkthrough after
personal practice. The project provides evidence to discuss; employment decisions
remain with employers. No messages or applications were sent on your behalf.
