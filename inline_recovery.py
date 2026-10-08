"""Ordered native/OCR blocks and explicit, auditable recovery flags."""
import hashlib
import json
from pathlib import Path


def merge_regions(regions):
    """Join overlapping/touching image tiles; retain separated illustrations."""
    result = []
    for region in regions:
        box = list(region)
        changed = True
        while changed:
            changed = False
            for other in result[:]:
                if box[0] <= other[2]+2 and other[0] <= box[2]+2 and box[1] <= other[3]+2 and other[1] <= box[3]+2:
                    box = [min(box[0],other[0]),min(box[1],other[1]),max(box[2],other[2]),max(box[3],other[3])]
                    result.remove(other)
                    changed = True
        result.append(box)
    return sorted(result,key=lambda b:(-b[3],b[0]))


def prepare_sections(sections):
    previous = None
    group = 0
    for section in sections:
        number = section['source_page']
        regions = merge_regions(section.get('image_regions', []))
        raw = section.get('raw_text', section.get('content',''))
        if not regions and not section.get('native_tables') and (len(raw.strip()) < 40 or '\ufffd' in raw or '(cid:' in raw):
            width,height = section.get('page_size',[612,792])
            regions = [[0,0,width,height]]
        flags = []
        for index,box in enumerate(regions,1):
            flags.append({'id':f'page-{number}-region-{index}','source_page':number,
                          'bbox':box,'status':'pending','reason':'Image region or unreadable page content'})
        if flags:
            if previous != number-1:
                group += 1
            previous = number
            for flag in flags:
                flag['image_sequence'] = group
        else:
            previous = None
        section['image_regions'] = regions
        section['ocr_flags'] = flags
        render_section(section)


def render_section(section):
    flags = section.get('ocr_flags',[])
    if not flags:
        return
    blocks = []
    for line in section.get('source_lines',[]):
        blocks.append({'kind':'native','bbox':line['bbox'],'text':line['text']})
    if not blocks and section.get('raw_text','').strip():
        blocks.append({'kind':'native','bbox':[0,0,0,section.get('page_size',[0,792])[1]],'text':section['raw_text']})
    results = {r['region']:r for r in section.get('image_ocr',[])}
    for index,flag in enumerate(flags,1):
        result = results.get(index)
        if result and result.get('markdown','').strip():
            flag['status'] = 'converted'
            flag['accuracy_verified'] = False
            flag['quality_warnings'] = result.get('quality_warnings', [])
            for concern in flag['quality_warnings']:
                warning = f'Image {index}: {concern}'
                if warning not in section.setdefault('warnings', []):
                    section['warnings'].append(warning)
            text = result['markdown']
        else:
            if result:
                flag['status'] = 'unresolved'
                flag['detail'] = result.get('status','No readable OCR content')
            text = f'[OCR {flag["status"].upper()}: {flag["id"]} — image content requires review]'
        blocks.append({'kind':'ocr','bbox':flag['bbox'],'text':text,'flag_id':flag['id']})
    blocks.sort(key=lambda b:(-b['bbox'][3],b['bbox'][0]))
    section['ordered_blocks'] = blocks
    section['content'] = '\n\n'.join(b['text'] for b in blocks)


def recover_sections(sections, pdf_path, assets_dir, enabled=True, workers=1):
    """Second pass: native extraction/flagging is complete before model loading."""
    prepare_sections(sections)
    destination = Path(assets_dir)
    destination.mkdir(parents=True,exist_ok=True)
    with open(pdf_path,'rb') as stream:
        digest = hashlib.file_digest(stream,'sha256').hexdigest()
    manifest = destination/'recovery_flags.json'
    def save_flags():
        manifest.write_text(json.dumps([flag for s in sections for flag in s.get('ocr_flags',[])],ensure_ascii=False,indent=2),encoding='utf-8')
    save_flags()
    (destination/'native_pass.json').write_text(json.dumps(sections,ensure_ascii=False),encoding='utf-8')
    pending = [s for s in sections if s.get('ocr_flags')]
    total_flags = sum(len(s["ocr_flags"]) for s in pending)
    processed_flags = 0
    print(f'[INFO] Native text conversion complete: {total_flags} OCR-flagged sections identified on {len(pending)} pages; {total_flags} remaining.',flush=True)
    if not enabled:
        print(f'[INFO] OCR disabled: {total_flags} flagged sections remain pending.', flush=True)
        return
    from ocr_parallel import choose_workers, bounded_results
    workers = choose_workers(workers, len(pending))
    import os
    device = os.environ.get('PDF_RAG_OCR_DEVICE', 'cpu')
    print(f'[INFO] OCR execution: {workers} worker(s), device {device}.', flush=True)
    def completed(section):
        nonlocal processed_flags
        for flag in section['ocr_flags']:
            processed_flags += 1
            status = 'text recovered, accuracy unverified' if flag['status'] == 'converted' else flag['status']
            print(f'[INFO] OCR checked {processed_flags} of {total_flags}: {flag["id"]} - {status}; {total_flags-processed_flags} remaining.', flush=True)
        if all(f['status'] == 'converted' for f in section['ocr_flags']):
            section['warnings'] = [w for w in section.get('warnings', []) if not w.startswith('Embedded images are not transcribed')]
        save_flags()
    if workers == 1:
        pipeline = None
        for section in pending:
            section, pipeline = recover_page(section, pdf_path, destination, digest, pipeline, (processed_flags,total_flags))
            completed(section)
    else:
        from concurrent.futures import ProcessPoolExecutor
        from multiprocessing import get_context
        import tempfile
        from image_ocr import prepare_images
        with tempfile.TemporaryDirectory(prefix='pdf_rag_queue_') as crop_folder:
            def tasks():
                offset = 0
                for section in pending:
                    if device.startswith('gpu'):
                        cached = read_recovery_cache(section, destination, digest)
                        section['image_ocr'] = cached or []
                        # Bounded CPU preparation overlaps the GPU workers.
                        try:
                            section['_prepared_images'] = prepare_images(section, pdf_path, Path(crop_folder)/str(section['source_page']))
                        except Exception as exc:
                            section['_prepared_images'] = {}
                            section['_preparation_error'] = str(exc)
                    yield (section, str(pdf_path), str(destination), digest, (offset,total_flags))
                    offset += len(section['ocr_flags'])
            with ProcessPoolExecutor(max_workers=workers, mp_context=get_context('spawn')) as executor:
                for index, result, error in bounded_results(executor, recover_page_worker, tasks(), workers):
                    section = pending[index]
                    if error is not None:
                        section['image_ocr'] = [{'region':i, 'markdown':'', 'status':f'Worker failed: {error}'} for i,_ in enumerate(section['ocr_flags'],1)]
                        render_section(section)
                        section.setdefault('warnings',[]).append(f'OCR worker failed: {error}')
                    else:
                        section.update(result)
                    section.pop('_prepared_images', None)
                    section.pop('_preparation_error', None)
                    completed(section)
    unresolved = sum(f['status'] != 'converted' for s in sections for f in s.get('ocr_flags',[]))
    print(f'[INFO] Recovery complete: {unresolved} unresolved flags remain visible in the document.',flush=True)
    print('[INFO] Recovery counts indicate text presence, not accuracy. All OCR text requires source review.', flush=True)


def recover_page(section, pdf_path, destination, digest, pipeline=None, progress=(0, 0)):
    from paddle_extract import create_pipeline
    from image_ocr import enrich_images
    destination = Path(destination)
    number = section['source_page']
    cache = recovery_cache_path(section, destination, digest)
    cached = read_recovery_cache(section, destination, digest)
    if cached and all(r.get('markdown','').strip() for r in cached):
        section['image_ocr'] = cached
    else:
        print(f'[INFO] Recovery pass: page {number}, sequence {section["ocr_flags"][0]["image_sequence"]}',flush=True)
        try:
            if section.get('_preparation_error'):
                raise RuntimeError('CPU image preparation failed: '+section['_preparation_error'])
            pipeline = pipeline or create_pipeline()
            section["image_ocr"] = cached or []
            section["_ocr_progress"] = progress
            enrich_images(section,pdf_path,pipeline,destination)
            cache.parent.mkdir(parents=True,exist_ok=True)
            cache.write_text(json.dumps(section['image_ocr'],ensure_ascii=False),encoding='utf-8')
        except Exception as exc:
            successful = {r['region']:r for r in section.get('image_ocr', []) if r.get('markdown','').strip()}
            section['image_ocr'] = [successful.get(i, {'region':i,'bbox':f['bbox'],'markdown':'','status':f'OCR failed: {exc}'}) for i,f in enumerate(section['ocr_flags'],1)]
            cache.parent.mkdir(parents=True,exist_ok=True)
            cache.write_text(json.dumps(section['image_ocr'],ensure_ascii=False),encoding='utf-8')
            section.setdefault('warnings',[]).append(f'OCR recovery failed on page {number}: {exc}')
    section.pop("_ocr_progress", None)
    section.pop("_prepared_images", None)
    section.pop("_preparation_error", None)
    render_section(section)
    return section, pipeline


_WORKER_PIPELINE = None


def recover_page_worker(section, pdf_path, destination, digest, progress):
    global _WORKER_PIPELINE
    section, _WORKER_PIPELINE = recover_page(section, pdf_path, destination, digest, _WORKER_PIPELINE, progress)
    return section


def recovery_cache_path(section, destination, digest):
    from ocr_settings import cache_policy
    policy = cache_policy()
    key = hashlib.sha256(json.dumps([digest, section['image_regions'], policy, section.get('orientation_correction', 0)]).encode()).hexdigest()[:24]
    return Path(destination)/f"page-{section['source_page']}"/f'recovery-{key}.json'


def read_recovery_cache(section, destination, digest):
    try:
        return json.loads(recovery_cache_path(section, destination, digest).read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return None
