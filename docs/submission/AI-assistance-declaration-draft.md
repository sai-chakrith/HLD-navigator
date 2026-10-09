# Academic integrity and AI-tool usage declaration — unsigned draft

Student: Sai Chakrith Sulluru. University: Amrita Viswa Vidyapeetham. Faculty guide: Dr. D. Palmani. Register/team ID: pending student-supplied details. Case study: CS1, HLD Navigator — AUTOSAR HLD Document Analysis Assistant.

This draft records known assistance and does not assert that the student has personally verified or can explain every artifact. The student must review, correct and personally sign the final declarations. No faculty approval or student signature has been supplied.

## Academic integrity

I will accurately disclose external source code, datasets, pretrained models, documents and assistance used in this submission. I will not represent synthetic fixtures, agent annotations or mocked outputs as independent human review or live measured model performance. I will state limitations, missing measurements and individual contributions accurately. The application supports engineering review; it does not certify automotive safety or AUTOSAR conformance.

## Known AI/model usage

| Tool/model | Purpose | Artifacts affected | Verified personally by student |
|---|---|---|---|
| OpenAI Codex coding assistant, including separate Developer/Tester chats | Implementation assistance, specifications, debugging, independently authored development tests, evidence review and packaging assistance | Python application, tests, scripts, documentation and submission drafts | Pending; student must enter Y/N accurately |
| Qwen2.5-0.5B-Instruct Q4_K_M, historical development experiment | Local answer-model feasibility baseline; failed earlier answer contract | Historical raw local-model evidence | Pending |
| Qwen2.5-7B-Instruct Q4_K_M | Local grounded answer experiment; final development run 29/30 raw contract, 8/12 useful complete answerable cases; semantic failures retained | Three complete fixed-case runs and actual API/model integration evidence | Pending |
| BGE-small F16 local embedding model | Learned retrieval comparison with lexical baseline | Vector index and retrieval experiment | Pending |

Assistance was not added as a Git co-author. Commit metadata does not replace this required disclosure. Separate AI Tester development checks do not replace an independent human architecture reviewer.

External references include the cited public KUKSA development documents and their recorded revision/license, official model/runtime sources, and any AUTOSAR explanatory material actually used. The reference hld_assistant repository was inspected for concepts; no source code was copied. Source/license and artifact hashes belong in the submission manifest.

Student signature: ____________________  Date: ____________________

Faculty approval/signature, where required: ____________________
