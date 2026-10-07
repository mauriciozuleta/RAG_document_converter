"""Isolated conversion process with durable logs and cancellation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid


def run_worker(request, cancel, emit=print):
    log_dir = Path(request['output_dir']) / '.conversion_logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / (uuid.uuid4().hex + '.log')
    emit(f'[INFO] Conversion log: {log_path}\n')
    python = Path(sys.executable)
    if python.name.lower() == 'pythonw.exe':
        python = python.with_name('python.exe')
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with tempfile.TemporaryDirectory(prefix='pdf_rag_job_') as folder:
        result = Path(folder) / 'result.json'
        job = Path(folder) / 'request.json'
        job.write_text(json.dumps({**request, 'result_path': str(result)}), encoding='utf-8')
        env = {**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8'}
        with log_path.open('wb') as log:
            process = subprocess.Popen([str(python), '-u', str(Path(__file__).with_name('conversion_worker.py')), str(job)],
                                       stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                       env=env, creationflags=flags)
            try:
                with log_path.open(encoding='utf-8', errors='replace') as reader:
                    while True:
                        chunk = reader.read(65536)
                        if chunk:
                            emit(chunk)
                        if process.poll() is not None:
                            # Drain any final buffered lines before reporting status.
                            for chunk in iter(lambda: reader.read(65536), ''):
                                emit(chunk)
                            break
                        if cancel.wait(.25):
                            if os.name == 'nt':
                                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                               creationflags=flags)
                            else:
                                process.terminate()
                            process.wait(timeout=15)
                            raise RuntimeError(f'Conversion cancelled. Completed page checkpoints and log remain at {log_path}')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
        if process.returncode != 0 or not result.exists():
            raise RuntimeError(f'Conversion worker failed (exit {process.returncode}). See {log_path}')
        return json.loads(result.read_text(encoding='utf-8'))
