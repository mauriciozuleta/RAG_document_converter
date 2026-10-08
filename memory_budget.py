"""Live memory availability and explicit headroom for measured OCR workers."""
import os
import subprocess


def snapshot(gpu=None):
    from ocr_parallel import available_memory_gb
    result = {'ram_gib': available_memory_gb()}
    if gpu:
        identifier = gpu.get('uuid') or os.environ.get('CUDA_VISIBLE_DEVICES', '0')
        response = subprocess.run(
            ['nvidia-smi', '-i', identifier, '--query-gpu=memory.free',
             '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=15)
        if response.returncode:
            raise RuntimeError('Cannot measure available NVIDIA memory: ' + response.stderr)
        result['vram_gib'] = float(response.stdout.strip()) / 1024
    return result


def worker_budget(reports, gpu=True):
    """Use largest measured process peak, with 25% growth allowance."""
    results = [r for key, report in reports.items()
               if key.startswith('gpu' if gpu else 'cpu') and report.get('ok')
               for r in report.get('results', [])]
    ram = max((r.get('rss_bytes', 0) / 1024**3 for r in results), default=0)
    vram = max((max(r.get('peak_reserved_vram_bytes', 0),
                    r.get('peak_allocated_vram_bytes', 0)) / 1024**3
                for r in results), default=0)
    return {'ram_per_worker_gib': max(2.5, ram * 1.25),
            'vram_per_worker_gib': max(2.5, vram * 1.25)}


def capacity(memory, budget, maximum=3):
    # Leave space for Windows, native extraction, the crop queue and CUDA context.
    ram_count = int(max(0, memory['ram_gib'] - 3) / budget['ram_per_worker_gib'])
    vram_count = maximum
    if 'vram_gib' in memory:
        vram_count = int(max(0, memory['vram_gib'] - 1) / budget['vram_per_worker_gib'])
    return max(0, min(maximum, ram_count, vram_count))
