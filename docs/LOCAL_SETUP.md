# Optional local models and OCR

Run from Code/HLD-navigator in the extracted submission. The default demo does
not require inference weights or Tesseract. Model provisioning needs network
access and several GB of disk; weights/runtime are intentionally not shipped.

```powershell
uv sync --frozen --extra dev
uv run python tools/setup_local_models.py
uv run python tools/setup_s1b_model.py
uv run python tools/serve_local_model.py answer
```

Keep the model server terminal open. In the separate API terminal set:

```powershell
$env:HLD_NAVIGATOR_CHAT_BACKEND='llama_cpp'
$env:HLD_NAVIGATOR_LOCAL_URL='http://127.0.0.1:18883'
$env:HLD_NAVIGATOR_CHAT_MODEL='qwen7b'
```

Start your provisioned API/UI as described in README. The demonstration launcher
disables model variables deliberately. Deterministic reviewed-field questions
may bypass inference; other model synthesis requires human review. The verified
30-case run supplies fixed evidence and does not establish end-to-end OEM accuracy.

For embedding setup, run `tools/serve_local_model.py embedding` and use its
printed settings in the API terminal; index the selected document first.

For OCR, install Tesseract through your administrator or `tools/setup_ocr.py`,
then set HLD_NAVIGATOR_OCR=1 and HLD_NAVIGATOR_TESSERACT to its installed executable.
The official installer may choose its standard Program Files location. Every OCR
page requires review. Real instruction-scan integration was observed; automotive
OCR accuracy, mixed image/text coverage and clean-machine setup remain unvalidated.
