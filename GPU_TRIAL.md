# GPU OCR trial

The isolated `.venv-gpu` uses PaddlePaddle GPU 3.3.1 (CUDA 12.6) with PaddleOCR 3.7.0. CPU and GPU environments remain separate. For automatic dependency setup and the default two-worker configuration, use `launch_app.bat`; see README.md. Blackwell cards use a separate CUDA 12.9 environment selected by the launcher. The manual CUDA 12.6 instructions below apply to older supported GPUs.

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

The trial uses one GPU worker and writes to a new timestamped folder under `verification/`. It reports model loading, individual OCR call times, throughput, total conversion time, GPU utilization, sampled total GPU memory, and this process's peak allocated VRAM in `gpu_benchmark.json`. Sampled total memory includes other applications. Check the generated JSON/Markdown against the PDF and inspect unresolved flags. This diagnostic script deliberately uses one worker; the application defaults to two after its startup test. A rerun into an existing output folder may reuse GPU checkpoints; use a fresh folder for timing comparisons.

For the app, run `./launch_app.ps1` or `./launch_gpu_app.ps1`. Both perform automatic setup, explicit NVIDIA selection and cached CPU/GPU benchmarks. Use `-Rebenchmark` to repeat those tests. GPU mode errors if CUDA is unavailable instead of silently switching to CPU. CPU and GPU recovery caches are separated.
