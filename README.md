# RAG_document_converter

Desktop PDF converter with native text/table extraction, inline OCR recovery, and optional NVIDIA GPU acceleration.

- Export JSON or Markdown for RAG, or CSV/Excel for detected tables.
- Detect image regions, recover their text with OCR, and retain source-page order.
- Save recovery checkpoints and show unresolved content flags.
- Run conversion in an isolated process with cancellation and durable logs.
- Use two GPU OCR workers plus a CPU coordinator by default.

## Run on Windows

Clone the repository (or run `git pull`), then double-click **launch_app.bat**, or run:

```powershell
.\launch_app.ps1
```

The launcher finds 64-bit Python 3.11?3.13, or installs Python 3.13 through Windows Package Manager if available. It creates isolated environments, installs missing dependencies. OCR models download when first needed for conversion or an explicit benchmark. First setup needs internet access and may download several GB. A compatible NVIDIA driver must already be installed.

Startup selects the NVIDIA device by UUID, independently of Windows GPU numbering. Blackwell cards such as RTX 5070 Ti use CUDA 12.9 packages; older supported cards use CUDA 12.6. Intel display GPUs are not selected for CUDA OCR.

Normal launch performs lightweight package and free-memory checks without loading OCR models or running benchmarks. Run `launch_app.ps1 -Rebenchmark` explicitly to benchmark CPU OCR and up to three GPU workers. **Two GPU OCR workers plus a CPU coordinator are the default**, subject to available memory. The coordinator renders/crops flagged regions and feeds a bounded queue. Each GPU worker retains its own OCR pipeline; results return to their original document positions. The worker selector offers three GPU workers when a saved three-worker benchmark passed and live memory permits. Without benchmark history, the maximum is two estimated workers. Every launch measures free RAM and NVIDIA VRAM, even when throughput benchmarks are cached. The limit uses the largest measured per-worker peak RAM and reserved/allocated VRAM, adds 25% headroom (minimum 2.5 GiB per worker), and reserves 3 GiB RAM for Windows/coordinator plus 1 GiB VRAM. Memory is checked again before OCR starts, and the log explains any reduction. If no worker fits, conversion stops with an explicit message. If the two-worker test fails, a successful one-worker test permits an explicit one-worker fallback. GPU failure is never silently replaced with CPU processing.

Reports and installation logs are under `.runtime/`; the latest profile is `.runtime/last_profile.json`. Current benchmark results are cached. If OCR settings change, startup can reuse same-hardware/driver measurements as an explicitly labeled estimate; it does not silently start new benchmarks. Models load when conversion starts. Small synthetic tests cannot predict throughput or peak memory for every document.

```powershell
.\launch_app.ps1 -Rebenchmark  # Repeat hardware tests
.\launch_app.ps1 -SetupOnly    # Prepare/test without opening the UI
.\launch_app.ps1 -CpuOnly      # Explicit CPU processing
```

The UI displays the selected device, free memory, and allowed worker count. It defaults to two OCR workers (or one when limited); select three manually when available. `launch_gpu_app.ps1` also uses automatic setup. Restart the app to use updated code; existing conversions retain their previous configuration.

For representative document-page measurements, see [GPU_TRIAL.md](GPU_TRIAL.md). Review recovered tables against the source, especially complex layouts and merged cells.

## Tests

```powershell
.\.venv\Scripts\python -m unittest -v
```

Local environments and generated verification outputs are excluded from Git. Two optional source-PDF tests require the external fixture described in the project wiki.

Memory limits are estimates from a small fixture, not a guarantee against allocation failures on larger pages. If other applications have been closed, relaunch to refresh the selectable limit; use `-Rebenchmark` to retry a failed OCR benchmark.

## OCR accuracy and readable output

The default OCR profile uses 300 DPI crops, English PP-OCRv5 recognition and adjusted text detection, validated on pages 2, 4 and 596 of the supplied tariff PDF. These changes invalidate old OCR checkpoints automatically. For multilingual recognition set `$env:PDF_RAG_OCR_MODEL = "PP-OCRv5_server_rec"` before launching; results still require review. See [ACCURACY_REVIEW.md](ACCURACY_REVIEW.md) for measured improvements and remaining errors.

The GUI defaults to JSON plus one combined Markdown document. Use **Open final document** after conversion; nested `_ocr_assets` folders are checkpoints/debug evidence. Simple tables render as Markdown; tables with merged cells retain HTML. OCR is explicitly unverified, with extra warnings for suspect text, low-confidence lines and symbols. No spelling or numeric values are silently guessed.

For Paddle builds reporting cuDNN 9.9, startup aligns the isolated GPU environment to nvidia-cudnn-cu12 9.9.0.52 and verifies GPU convolution. Paddle 3.3.1 cu126 Windows has inconsistent dependency metadata pinning 9.5: this targeted override produces a known `pip check` conflict. System CUDA files are unchanged.

References: [PaddleOCR detection settings](https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/pipeline_usage/OCR.html), [official English recognition model](https://huggingface.co/PaddlePaddle/en_PP-OCRv5_mobile_rec).

## Sideways and upside-down native pages

Native extraction detects dominant character direction and normalizes 90/180/270-degree pages before grouping lines and table cells. The original PDF is unchanged. JSON records `orientation_correction`; coordinates and page dimensions describe the normalized view. At least 20 nonblank characters and 80% directional agreement are required, so small rotated labels do not rotate an otherwise upright page. Ambiguous/image-only pages retain existing OCR/review behavior. OCR crops use the same rotation, and table/recovery caches account for the new coordinate policy.

Verified on Saint Lucia tariff PDF pages 599?627: sideways pages normalize while upright neighbors remain unchanged; every native character is preserved. Layout ordering and spacing remain heuristics, not guaranteed semantic table reconstruction.
