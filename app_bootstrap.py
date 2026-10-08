"""Windows first-run setup, device detection and cached CPU/GPU benchmarks."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from memory_budget import snapshot, worker_budget, capacity

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'.runtime'


def detect_gpus():
    fields='index,name,uuid,compute_cap,driver_version,memory.total'
    try:
        result=subprocess.run(['nvidia-smi',f'--query-gpu={fields}','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15)
        if result.returncode:
            raise RuntimeError('nvidia-smi could not report CUDA hardware: '+result.stderr.strip())
        gpus=[]
        for line in result.stdout.strip().splitlines():
            index,name,uuid,capability,driver,memory=[v.strip() for v in line.split(',')]
            gpus.append(dict(index=int(index),name=name,uuid=uuid,compute_capability=float(capability),driver=driver,memory_mib=int(memory)))
        return gpus
    except FileNotFoundError:
        return []


def cuda_channel(gpu):
    return 'cu129' if gpu['compute_capability']>=10 else 'cu126'


def signature(gpu):
    files=['requirements.txt','requirements-ocr.txt','requirements-gpu.txt','hardware_benchmark.py','paddle_extract.py','ocr_settings.py']
    data={'gpu':gpu,'python':list(sys.version_info[:2]),'cpu':platform.processor(),'version':1,'ocr_model':os.environ.get('PDF_RAG_OCR_MODEL'),
          'files':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:24]


def run_logged(command,log_path,env=None,timeout=1800):
    """Keep setup visible, with durable detail logs and bounded subprocesses."""
    log_path=Path(log_path);log_path.parent.mkdir(parents=True,exist_ok=True)
    print(f'[SETUP] {command[0]}: details in {log_path}',flush=True)
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    with log_path.open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=flags)
        start=time.monotonic();last=start
        try:
            while process.poll() is None:
                now=time.monotonic()
                if now-start>timeout:
                    raise TimeoutError(f'Timed out after {timeout}s; see {log_path}')
                if now-last>=20:
                    print(f'[SETUP] Still working ({int(now-start)}s). Log: {log_path.name}',flush=True);last=now
                time.sleep(.25)
        finally:
            if process.poll() is None:
                if os.name=='nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
                else:process.kill()
                process.wait()
    if process.returncode:
        tail=log_path.read_text(encoding='utf-8',errors='replace')[-1800:]
        raise RuntimeError(f'Command failed ({process.returncode}): {tail}\nLog: {log_path}')


PROBE = '''import json, importlib.metadata as m
import paddle, tkinter, tkinterdnd2, pypdfium2, openpyxl, pdfminer
from paddleocr import PPStructureV3
import os
mode=os.environ['PDF_RAG_OCR_DEVICE']
if mode.startswith('gpu'):
    assert paddle.is_compiled_with_cuda(), 'CPU-only Paddle installed'
    paddle.set_device(mode)
    assert float(paddle.matmul(paddle.ones([8,8]),paddle.ones([8,8]))[0,0])==8
    paddle.device.synchronize()
    paddle.nn.Conv2D(3,4,3)(paddle.ones([1,3,16,16]))
    paddle.device.synchronize()
print('RUNTIME='+json.dumps({'paddle':paddle.__version__,'ocr':m.version('paddleocr'),'cuda':str(paddle.version.cuda()),'cudnn_build':str(paddle.version.cudnn()),'cudnn_package':m.version('nvidia-cudnn-cu12') if mode.startswith('gpu') else None,'gpu':paddle.device.cuda.get_device_name(0) if mode.startswith('gpu') else None}))
'''


LIGHT_PROBE = '''import importlib.metadata as m, importlib.util, json, os, re
from pathlib import Path
for name in ['paddle','paddleocr','tkinter','tkinterdnd2','pypdfium2','openpyxl','pdfminer']:
    assert importlib.util.find_spec(name), name
source=(Path(importlib.util.find_spec('paddle').origin).parent/'version'/'__init__.py').read_text(encoding='utf-8')
def version(name):
    match=re.search(name+r"\\s*=\\s*['\\\"]([^'\\\"]+)['\\\"]",source)
    return match.group(1) if match else ''
gpu=os.environ['PDF_RAG_OCR_DEVICE'].startswith('gpu')
print('RUNTIME='+json.dumps({'paddle':m.version('paddlepaddle-gpu' if gpu else 'paddlepaddle'),'ocr':m.version('paddleocr'),'cuda':version('cuda_version'),'cudnn_build':version('cudnn_version'),'cudnn_package':m.version('nvidia-cudnn-cu12') if gpu else None}))
'''


def probe(python,device,env,quick=True):
    if not Path(python).exists():return None
    try:
        result=subprocess.run([str(python),'-c',LIGHT_PROBE if quick else PROBE],env={**env,'PDF_RAG_OCR_DEVICE':device},capture_output=True,text=True,timeout=20 if quick else 120)
        if result.returncode:return None
        line=next(line for line in result.stdout.splitlines() if line.startswith('RUNTIME='))
        return json.loads(line[8:])
    except (OSError,subprocess.TimeoutExpired,StopIteration,ValueError):return None


def ensure_environment(device,gpu,env):
    channel=cuda_channel(gpu) if gpu else None
    folder=ROOT/('.venv' if device=='cpu' else ('.venv-gpu' if channel=='cu126' else '.venv-gpu-cu129'))
    python=folder/'Scripts'/'python.exe'
    found=probe(python,device,env)
    expected_cuda='12.9' if channel=='cu129' else '12.6'
    if found and found['paddle']=='3.3.1' and found['ocr']=='3.7.0' and (device=='cpu' or found['cuda'].startswith(expected_cuda)):
        print(f'[SETUP] Existing {device} environment verified: {python}',flush=True)
        return repair_cudnn(python, device, found, env)
    # Never replace an environment being used by a running conversion.
    if python.exists():
        folder=ROOT/'.runtime'/('cpu-py'+str(sys.version_info.minor) if device=='cpu' else channel+'-py'+str(sys.version_info.minor))
        python=folder/'Scripts'/'python.exe'
        found=probe(python,device,env)
        if found and found['paddle']=='3.3.1' and found['ocr']=='3.7.0' and (device=='cpu' or found['cuda'].startswith(expected_cuda)):
            return repair_cudnn(python, device, found, env)
    run_logged([sys.executable,'-m','venv',str(folder)],STATE/f'{device[:3]}-venv.log',env)
    if device.startswith('gpu'):
        run_logged([str(python),'-m','pip','install','paddlepaddle-gpu==3.3.1','--index-url',f'https://www.paddlepaddle.org.cn/packages/stable/{channel}/'],STATE/f'{channel}-install.log',env,timeout=3600)
        requirements='requirements-gpu.txt'
    else:requirements='requirements-ocr.txt'
    run_logged([str(python),'-m','pip','install','-r',str(ROOT/requirements)],STATE/f'{device[:3]}-requirements.log',env,timeout=3600)
    run_logged([str(python),'-m','pip','check'],STATE/f'{device[:3]}-check.log',env)
    found=probe(python,device,env)
    if not found:
        raise RuntimeError(f'{device} runtime verification failed. Check .runtime logs and the NVIDIA driver. No silent CPU fallback was made.')
    return repair_cudnn(python, device, found, env)


def repair_cudnn(python, device, found, env):
    # Paddle 3.3.1 cu126 Windows metadata pins 9.5 although its binary uses 9.9.
    if device.startswith('gpu') and found.get('cudnn_build', '').startswith('9.9'):
        if found.get('cudnn_package') != '9.9.0.52':
            print('[SETUP] Aligning isolated cuDNN runtime with Paddle build 9.9.', flush=True)
            run_logged([str(python), '-m', 'pip', 'install', '--no-deps', '--upgrade',
                        'nvidia-cudnn-cu12==9.9.0.52'], STATE/'cudnn-repair.log', env, timeout=3600)
            verified = probe(python, device, env, quick=False)
            if not verified or verified.get('cudnn_package') != '9.9.0.52':
                raise RuntimeError('cuDNN repair failed GPU convolution verification.')
    return python


def benchmark(python,device,workers,folder,env):
    output=folder/f'{device[:3]}-{workers}.json'
    print(f'[BENCHMARK] Testing {device}, {workers} worker(s) on a small table.',flush=True)
    try:
        prior = {}
        for count in range(1, workers):
            previous = folder/f'{device[:3]}-{count}.json'
            if previous.exists():
                prior[f'{device[:3]}{count}'] = json.loads(previous.read_text(encoding='utf-8'))
        memory = snapshot({'uuid': env.get('CUDA_VISIBLE_DEVICES', '0')} if device.startswith('gpu') else None)
        budget = worker_budget(prior, device.startswith('gpu'))
        if capacity(memory, budget, workers) < workers:
            print(f'[MEMORY] Skipping {workers}-worker benchmark: available {memory}; budget {budget}.', flush=True)
            return {'ok': False, 'skipped_memory': True, 'memory': memory, 'budget': budget}
        run_logged([str(python),'-u',str(ROOT/'hardware_benchmark.py'),'--device',device,'--workers',str(workers),'--out',str(output)],output.with_suffix('.log'),{**env,'PDF_RAG_OCR_DEVICE':device},timeout=300)
        report=json.loads(output.read_text(encoding='utf-8'))
    except (RuntimeError,TimeoutError,OSError,ValueError) as exc:
        report={'ok':False,'device':device,'workers':workers,'error':str(exc)}
        output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    if report['ok']:
        print(f'[BENCHMARK] {device} x{workers}: {report["images_per_minute"]:.1f} small images/minute.',flush=True)
    else:print(f'[BENCHMARK] {device} x{workers} failed or timed out; see {output}',flush=True)
    return report


def select_configuration(gpu,reports):
    if gpu:
        if reports['gpu2'].get('ok'):
            return 'gpu:0',2,'Two GPU OCR workers + CPU coordinator. Startup benchmark passed.'
        if reports['gpu1'].get('ok'):
            return 'gpu:0',1,'Two GPU workers failed the startup test. Using one GPU worker; see .runtime benchmarks.'
        raise RuntimeError('NVIDIA OCR failed both tests. Check benchmark logs/driver; use -CpuOnly only if you want CPU OCR.')
    if not reports['cpu'].get('ok'):
        raise RuntimeError('CPU OCR benchmark failed. Check .runtime benchmark logs.')
    return 'cpu',2,'CPU OCR selected: no NVIDIA GPU detected, or CPU-only launch requested.'


@contextlib.contextmanager
def setup_lock():
    STATE.mkdir(exist_ok=True)
    with (STATE/'setup.lock').open('a+b') as stream:
        stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
        import msvcrt
        try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise RuntimeError('Another setup is running. Wait for that setup window to finish.')
        try:yield
        finally:
            stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebenchmark',action='store_true')
    parser.add_argument('--cpu-only',action='store_true')
    parser.add_argument('--no-launch',action='store_true')
    args=parser.parse_args()
    if os.name!='nt':raise RuntimeError('Automatic launcher currently supports Windows.')
    if not (3,11)<=sys.version_info[:2]<(3,14):raise RuntimeError('Use 64-bit Python 3.11-3.13 (launcher prefers 3.13).')
    import struct
    if struct.calcsize('P') != 8:raise RuntimeError('Install 64-bit Python 3.13 before launching.')
    env={**os.environ,'PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK':'True','PYTHONIOENCODING':'utf-8','PYTHONUNBUFFERED':'1'}
    with setup_lock():
        gpus=[] if args.cpu_only else detect_gpus()
        gpu=max(gpus,key=lambda g:g['memory_mib']) if gpus else None
        if gpu:
            env['CUDA_VISIBLE_DEVICES']=gpu['uuid']
            print(f'[SETUP] NVIDIA GPU: {gpu["name"]}, {gpu["memory_mib"]} MiB; package {cuda_channel(gpu)}. Intel display GPUs are not CUDA devices.',flush=True)
        else:print('[SETUP] CPU mode: no NVIDIA GPU detected or CPU-only requested.',flush=True)
        cpu_python=ensure_environment('cpu',None,env) if not gpu or args.rebenchmark else None
        gpu_python=ensure_environment('gpu:0',gpu,env) if gpu else None
        key=signature(gpu);folder=STATE/'benchmarks'/key;folder.mkdir(parents=True,exist_ok=True)
        profile_path=folder/'profile.json'
        try:profile=json.loads(profile_path.read_text(encoding='utf-8')) if not args.rebenchmark else None
        except (OSError,ValueError):profile=None
        if not profile and not args.rebenchmark:
            try:
                previous = json.loads((STATE/'last_profile.json').read_text(encoding='utf-8'))
            except (OSError, ValueError):
                previous = {}
            same_gpu = gpu and (previous.get('gpu') or {}).get('uuid') == gpu['uuid'] and (previous.get('gpu') or {}).get('driver') == gpu['driver']
            reports = previous.get('benchmarks', {}) if same_gpu else {}
            profile = {'device':'gpu:0' if gpu else 'cpu', 'workers':2, 'gpu':gpu,
                       'benchmarks':reports, 'benchmark_current':False}
        if args.rebenchmark:
            print('[SETUP] Preparing OCR models (first use may download model files).', flush=True)
            run_logged([str(cpu_python), '-u', '-c', 'from paddle_extract import create_pipeline; create_pipeline()'], folder/'model-prepare.log', {**env, 'PDF_RAG_OCR_DEVICE':'cpu'}, timeout=1800)
            reports={'cpu':benchmark(cpu_python,'cpu',1,folder,env)}
            if gpu:
                reports['gpu1']=benchmark(gpu_python,'gpu:0',1,folder,env)
                reports['gpu2']=benchmark(gpu_python,'gpu:0',2,folder,env)
            device,workers,note=select_configuration(gpu,reports)
            profile={'device':device,'workers':workers,'note':note,'gpu':gpu,'benchmarks':reports,'benchmark_current':True}
            profile_path.write_text(json.dumps(profile,indent=2),encoding='utf-8')
        reports = profile['benchmarks']
        memory = snapshot(gpu)
        budget = worker_budget(reports, bool(gpu))
        limit = capacity(memory, budget, 3 if gpu else 2)
        print(f'[MEMORY] Available: {memory}; per-worker budget: {budget}; capacity: {limit}.', flush=True)
        if args.rebenchmark and gpu and limit >= 2 and reports.get('gpu2', {}).get('skipped_memory'):
            reports['gpu2'] = benchmark(gpu_python, 'gpu:0', 2, folder, env)
            budget = worker_budget(reports)
            memory = snapshot(gpu)
            limit = capacity(memory, budget)
        if args.rebenchmark and gpu and reports.get('gpu2', {}).get('ok') and limit >= 3 and ('gpu3' not in reports or reports['gpu3'].get('skipped_memory')):
            reports['gpu3'] = benchmark(gpu_python, 'gpu:0', 3, folder, env)
            budget = worker_budget(reports)
            memory = snapshot(gpu)
            limit = capacity(memory, budget)
        if gpu and reports:
            validated = [n for n in range(1, limit + 1) if reports.get(f'gpu{n}', {}).get('ok')]
            limit = max(validated, default=0)
        elif gpu:
            limit = min(limit, 2)
        if limit == 0:
            raise RuntimeError('Insufficient available memory for a validated OCR worker. Free memory and relaunch.')
        profile.update(memory=memory, memory_budget=budget, max_workers=limit)
        profile['workers'] = min(2, limit)
        profile['note'] = f"{profile['workers']} default OCR worker(s); memory/benchmark limit: {limit}. RAM free: {memory['ram_gib']:.1f} GiB" + (f"; VRAM free: {memory['vram_gib']:.1f} GiB." if gpu else '.')
        if not profile.get('benchmark_current', True):
            profile['note'] += ' Estimated capacity; use -Rebenchmark for current OCR measurements.'
        profile_path.write_text(json.dumps(profile,indent=2),encoding='utf-8')
        print(f'[SETUP] {profile["note"]} Report: {profile_path}',flush=True)
        (STATE/'last_profile.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
        env.update(PDF_RAG_BOOTSTRAPPED='1',PDF_RAG_OCR_DEVICE=profile['device'],PDF_RAG_OCR_WORKERS=str(profile['workers']),PDF_RAG_DEVICE_NAME=gpu['name'] if gpu else 'CPU',PDF_RAG_STARTUP_NOTE=profile['note'])
        env['PDF_RAG_MAX_WORKERS'] = str(limit)
        env['PDF_RAG_MEMORY_BUDGET'] = json.dumps(budget)
        python=gpu_python if profile['device'].startswith('gpu') else cpu_python
    if not args.no_launch:
        flags=subprocess.CREATE_NO_WINDOW
        subprocess.Popen([str(python.with_name('pythonw.exe')),str(ROOT/'pdf_to_rag_ui.py')],cwd=ROOT,env=env,creationflags=flags)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(f'[SETUP ERROR] {exc}',file=sys.stderr,flush=True)
        raise SystemExit(1)
