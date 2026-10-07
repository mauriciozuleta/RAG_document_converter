# RAG_document_converter

Desktop PDF converter with native text/table extraction, inline OCR recovery, and optional NVIDIA GPU acceleration.

- Export JSON or Markdown for RAG, or CSV/Excel for detected tables.
- Detect image regions, recover their text with OCR, and retain source-page order.
- Save recovery checkpoints and show unresolved content flags.
- Run conversion in an isolated process with cancellation and durable logs.
- Use one or two memory-checked CPU OCR workers, or one GPU worker.

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-ocr.txt
.\launch_app.ps1
```

OCR models download on first use. Native extraction works without OCR; automatic OCR is enabled in the GUI. Review recovered tables against the source, especially complex layouts and merged cells.

For the separate GPU environment, launcher, and measured trial, see [GPU_TRIAL.md](GPU_TRIAL.md). A compatible NVIDIA GPU and driver are required.

## Tests

```powershell
.\.venv\Scripts\python -m unittest -v
```

Local environments and generated verification outputs are excluded from Git. Two optional source-PDF tests require the external fixture described in the project wiki.
