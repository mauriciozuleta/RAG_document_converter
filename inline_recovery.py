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


def recover_sections(sections, pdf_path, assets_dir, enabled=True):
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
    print(f'[INFO] Native pass complete. {sum(len(s["ocr_flags"]) for s in pending)} flagged regions on {len(pending)} pages.',flush=True)
    if not enabled:
        return
    from paddle_extract import create_pipeline
    from image_ocr import enrich_images
    pipeline = None
    for section in pending:
        number = section['source_page']
        key = hashlib.sha256(json.dumps([digest,section['image_regions'],'inline-v1']).encode()).hexdigest()[:24]
        cache = destination/f'page-{number}'/f'recovery-{key}.json'
        try:
            cached = json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else None
        except (ValueError,OSError):
            cached = None
        if cached and all(r.get('markdown','').strip() for r in cached):
            section['image_ocr'] = cached
        else:
            print(f'[INFO] Recovery pass: page {number}, sequence {section["ocr_flags"][0]["image_sequence"]}',flush=True)
            try:
                pipeline = pipeline or create_pipeline()
                section["image_ocr"] = cached or []
                enrich_images(section,pdf_path,pipeline,destination)
                cache.parent.mkdir(parents=True,exist_ok=True)
                cache.write_text(json.dumps(section['image_ocr'],ensure_ascii=False),encoding='utf-8')
            except Exception as exc:
                successful = {r['region']:r for r in section.get('image_ocr', []) if r.get('markdown','').strip()}
                section['image_ocr'] = [successful.get(i, {'region':i,'bbox':f['bbox'],'markdown':'','status':f'OCR failed: {exc}'}) for i,f in enumerate(section['ocr_flags'],1)]
                cache.parent.mkdir(parents=True,exist_ok=True)
                cache.write_text(json.dumps(section['image_ocr'],ensure_ascii=False),encoding='utf-8')
                section.setdefault('warnings',[]).append(f'OCR recovery failed on page {number}: {exc}')
        render_section(section)
        if all(f['status'] == 'converted' for f in section['ocr_flags']):
            section['warnings'] = [w for w in section.get('warnings', []) if not w.startswith('Embedded images are not transcribed')]
        save_flags()
    unresolved = sum(f['status'] != 'converted' for s in sections for f in s.get('ocr_flags',[]))
    print(f'[INFO] Recovery complete: {unresolved} unresolved flags remain visible in the document.',flush=True)
