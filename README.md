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

The launcher finds 64-bit Python 3.11?3.13, or installs Python 3.13 through Windows Package Manager if available. It creates isolated environments, installs missing dependencies, and downloads OCR models. First setup needs internet access and may download several GB. A compatible NVIDIA driver must already be installed.

Startup selects the NVIDIA device by UUID, independently of Windows GPU numbering. Blackwell cards such as RTX 5070 Ti use CUDA 12.9 packages; older supported cards use CUDA 12.6. Intel display GPUs are not selected for CUDA OCR.

First setup benchmarks CPU OCR and up to three GPU workers on a small synthetic table, checking available memory before each test. **Two GPU OCR workers plus a CPU coordinator are the default** when the two-worker test succeeds. The coordinator renders/crops flagged regions and feeds a bounded queue. Each GPU worker retains its own OCR pipeline; results return to their original document positions. The worker selector offers three GPU workers when its benchmark passes and live memory permits. Every launch measures free RAM and NVIDIA VRAM, even when throughput benchmarks are cached. The limit uses the largest measured per-worker peak RAM and reserved/allocated VRAM, adds 25% headroom (minimum 2.5 GiB per worker), and reserves 3 GiB RAM for Windows/coordinator plus 1 GiB VRAM. Memory is checked again before OCR starts, and the log explains any reduction. If no worker fits, conversion stops with an explicit message. If the two-worker test fails, a successful one-worker test permits an explicit one-worker fallback. GPU failure is never silently replaced with CPU processing.

Reports and installation logs are under `.runtime/`; the latest profile is `.runtime/last_profile.json`. Benchmarks are cached for the hardware, driver and relevant dependency configuration. Later launches verify the environment and reuse the profile. Small synthetic tests cannot predict throughput or peak memory for every document.

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
