# GPU OCR trial

The isolated `.venv-gpu` uses PaddlePaddle GPU 3.3.1 (CUDA 12.6) with PaddleOCR 3.7.0. The ordinary `.venv` and CPU launcher remain separate.

Recreate the GPU environment:

```powershell
python -m venv .venv-gpu
.\.venv-gpu\Scripts\python -m pip install paddlepaddle-gpu==3.3.1 --index-url https://www.paddlepaddle.org.cn/packages/stable/cu126/
.\.venv-gpu\Scripts\python -m pip install -r requirements-gpu.txt
```

Do not install `requirements-ocr.txt` into this environment: it selects CPU Paddle.

After the current conversion finishes, benchmark representative pages that contain the flagged images:

```powershell
.\.venv-gpu\Scripts\python gpu_trial.py 'C:\path\document.pdf' --pages '12,18-20'
```

The trial uses one GPU worker and writes to a new timestamped folder under `verification/`. It reports model loading, individual OCR call times, throughput, total conversion time, GPU utilization, sampled total GPU memory, and this process's peak allocated VRAM in `gpu_benchmark.json`. Sampled total memory includes other applications. Check the generated JSON/Markdown against the PDF and inspect unresolved flags before deciding whether to test two GPU workers. A rerun into an existing output folder may reuse GPU checkpoints; use a fresh folder for timing comparisons.

For the GPU app, run `./launch_gpu_app.ps1`. It keeps GPU OCR at one worker. The existing `launch_app.ps1` continues to use the CPU environment. GPU mode errors if CUDA is unavailable instead of silently switching to CPU. CPU and GPU recovery caches are separated.
