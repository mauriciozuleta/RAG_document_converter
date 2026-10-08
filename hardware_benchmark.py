"""Startup OCR smoke/throughput benchmark; one fresh process per model copy."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from multiprocessing import get_context
import os
from pathlib import Path
import threading
import time


def make_fixture(path):
    from PIL import Image, ImageDraw, ImageFont
    image=Image.new('RGB',(900,420),'white');draw=ImageDraw.Draw(image)
    try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',28)
    except OSError:font=ImageFont.load_default(size=28)
    draw.text((30,15),'OCR BENCHMARK',fill='black',font=font)
    for x in [30,360,670,870]:draw.line((x,75,x,375),fill='black',width=2)
    for y in [75,150,225,300,375]:draw.line((30,y,870,y),fill='black',width=2)
    for row,values in enumerate([('Item','Description','Quantity'),('00123','Sample table','45'),('00456','Second row','67'),('00789','Final row','89')]):
        for x,value in zip([40,370,680],values):draw.text((x,90+row*75),value,fill='black',font=font)
    image.save(path);image.close()


def worker(image_path,device,barrier):
    os.environ['PDF_RAG_OCR_DEVICE']=device
    os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK']='True'
    from paddle_extract import create_pipeline
    import psutil
    start=time.perf_counter();pipeline=create_pipeline();load=time.perf_counter()-start
    if barrier is not None:barrier.wait(timeout=240)
    start=time.perf_counter();times=[];texts=[]
    for _ in range(2):
        before=time.perf_counter()
        results=list(pipeline.predict(input=image_path))
        if device.startswith('gpu'):
            import paddle
            paddle.device.synchronize()
        times.append(time.perf_counter()-before)
        texts.append('\n'.join(r.markdown.get('markdown_texts','') for r in results))
    result={'pid':os.getpid(),'load_seconds':load,'start':start,'finish':time.perf_counter(),'inference_seconds':times,'recognized':any('benchmark' in t.lower() for t in texts),'markdown':texts[-1], 'rss_bytes':getattr(psutil.Process().memory_info(), 'peak_wset', psutil.Process().memory_info().rss)}
    if device.startswith('gpu'):
        import paddle
        result['peak_allocated_vram_bytes']=paddle.device.cuda.max_memory_allocated()
        result['peak_reserved_vram_bytes']=paddle.device.cuda.max_memory_reserved()
        result['gpu_name']=paddle.device.cuda.get_device_name(0)
    return result


def run(device,workers,output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    fixture=output.with_suffix('.png');make_fixture(fixture)
    started=time.perf_counter();report={'device':device,'workers':workers,'ok':False}
    samples=[];stop=threading.Event()
    def monitor():
        import subprocess
        while not stop.is_set():
            try:
                identifier=os.environ.get('CUDA_VISIBLE_DEVICES','0')
                p=subprocess.run(['nvidia-smi','-i',identifier,'--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                memory,utilization=map(float,p.stdout.strip().split(','))
                samples.append({'seconds':time.perf_counter()-started,'total_used_vram_mib':memory,'gpu_utilization_percent':utilization})
            except Exception:pass
            stop.wait(1)
    monitor_thread=threading.Thread(target=monitor,daemon=True);monitor_thread.start()
    try:
        context=get_context('spawn')
        with context.Manager() as manager:
            barrier=manager.Barrier(workers) if workers>1 else None
            with ProcessPoolExecutor(max_workers=workers,mp_context=context) as pool:
                futures=[pool.submit(worker,str(fixture),device,barrier) for _ in range(workers)]
                results=[future.result() for future in futures]
        span=max(r['finish'] for r in results)-min(r['start'] for r in results)
        report.update(ok=all(r['recognized'] for r in results),results=results,images_per_minute=workers*2*60/span,wall_inference_seconds=span)
    except Exception as exc:report['error']=str(exc)
    finally:
        stop.set();monitor_thread.join(timeout=6)
        report.update(total_seconds=time.perf_counter()-started,gpu_samples=samples,fixture_note='Small synthetic table; not a prediction of full-document speed or peak memory.')
        output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',choices=['cpu','gpu:0'],required=True)
    parser.add_argument('--workers',type=int,choices=[1,2,3],required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    report=run(args.device,args.workers,args.out)
    print(json.dumps({k:v for k,v in report.items() if k not in ('results','gpu_samples')}),flush=True)
    return 0 if report['ok'] else 1


if __name__=='__main__':
    raise SystemExit(main())
