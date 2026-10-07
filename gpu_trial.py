"""One-GPU-worker OCR trial with inference timings and GPU telemetry."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf')
    parser.add_argument('--pages',required=True,help='Representative pages, e.g. 12,18-20')
    parser.add_argument('--out',default=None)
    args=parser.parse_args()
    os.environ['PDF_RAG_OCR_DEVICE']='gpu:0'
    output=Path(args.out or (Path('verification')/('gpu-trial-'+time.strftime('%Y%m%d-%H%M%S')))).resolve()
    output.mkdir(parents=True,exist_ok=True)
    import paddle
    if not paddle.is_compiled_with_cuda() or paddle.device.cuda.device_count()<1:
        raise RuntimeError('Use .venv-gpu/Scripts/python.exe; CUDA GPU required.')
    import paddle_extract
    from pdf_to_rag import process_pdf
    original=paddle_extract.create_pipeline
    stats={'device':paddle.device.cuda.get_device_name(0),'pages':args.pages,'model_load_seconds':None,'inference_seconds':[],'gpu_samples':[], 'outputs':[]}
    stop=threading.Event()
    def sample():
        while not stop.is_set():
            try:
                result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits','-i','0'],capture_output=True,text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                memory,utilization=map(float,result.stdout.strip().split(','))
                stats['gpu_samples'].append({'seconds':round(time.monotonic()-started,2),'used_vram_mib':memory,'utilization_percent':utilization})
            except Exception:
                pass
            stop.wait(1)
    class TimedPipeline:
        def __init__(self,pipeline): self.pipeline=pipeline
        def predict(self,**kwargs):
            before=time.monotonic()
            try:
                result=list(self.pipeline.predict(**kwargs))
                paddle.device.synchronize()
                return result
            finally:
                elapsed=time.monotonic()-before
                stats['inference_seconds'].append(elapsed)
                print(f'[BENCHMARK] Image {len(stats["inference_seconds"])}: {elapsed:.2f}s',flush=True)
    def create():
        before=time.monotonic()
        pipeline=original()
        paddle.device.synchronize()
        stats['model_load_seconds']=time.monotonic()-before
        return TimedPipeline(pipeline)
    paddle_extract.create_pipeline=create
    started=time.monotonic()
    monitor=threading.Thread(target=sample,daemon=True);monitor.start()
    try:
        stats['outputs']=process_pdf(args.pdf,str(output),output_format='both',engine='paddle',pages=args.pages,ocr_workers=1)
    finally:
        stop.set();monitor.join(timeout=6)
        stats['total_seconds']=time.monotonic()-started
        times=stats['inference_seconds']
        stats['mean_inference_seconds']=sum(times)/len(times) if times else None
        stats['inferences_per_minute']=60*len(times)/sum(times) if times and sum(times) else None
        stats['peak_process_allocated_vram_bytes']=paddle.device.cuda.max_memory_allocated()
        stats['peak_total_gpu_used_mib']=max((s['used_vram_mib'] for s in stats['gpu_samples']),default=None)
        stats['telemetry_note']='nvidia-smi includes all GPU applications; allocator peak is this process. Timing includes model failures if any; inspect output flags and compare PDF accuracy.'
        report=output/'gpu_benchmark.json'
        report.write_text(json.dumps(stats,indent=2),encoding='utf-8')
        print(f'[BENCHMARK] Report: {report}',flush=True)


if __name__=='__main__':
    main()
