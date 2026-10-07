"""Native-first table conversion with durable per-page checkpoints."""
import hashlib
import json
from pathlib import Path
import time
from pdfminer.high_level import extract_pages
from pdfminer.pdfpage import PDFPage
from native_tables import extract_grids
from table_export import export_tables, TableParser


def replace_checkpoint(temporary, target):
    # Windows sync/indexing can briefly hold the destination open.
    for attempt in range(6):
        try:
            temporary.replace(target)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.1 * (attempt + 1))


def convert_tables(pdf_path, output_dir, base_name, fmt, engine, selected=None):
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    with open(pdf_path, 'rb') as source:
        total_pages = sum(1 for _ in PDFPage.get_pages(source))
        source.seek(0)
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    pages = selected if selected is not None else list(range(total_pages))
    if not pages or any(n < 0 or n >= total_pages for n in pages):
        raise ValueError('Requested page range exceeds the document length.')
    cache = destination / '.table_checkpoints' / f'{digest[:20]}-v1-{engine}'
    cache.mkdir(parents=True, exist_ok=True)
    stored = {}
    for n in pages:
        path = cache / f'page-{n+1}.json'
        if path.exists():
            try:
                stored[n] = json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                pass
    pending = [n for n in pages if n not in stored]
    layouts = iter(extract_pages(pdf_path, page_numbers=pending)) if pending else iter(())
    started = time.monotonic()
    paths, sections, report = [], [], []
    pipeline = None
    print(f'[INFO] {len(pages)} pages; {len(stored)} cached. Native tables first. OCR fallback: {engine == "paddle"}.', flush=True)
    for index,n in enumerate(pages,1):
        cached = n in stored
        if cached:
            record = stored.pop(n)
        else:
            page = next(layouts)
            tables, text = extract_grids(page)
            method = 'native'
            status = 'tables extracted' if tables else 'No continuous ruled table detected; review page (borderless/complex tables are not inferred).'
            needs_ocr = len(text.strip()) < 40 or '\ufffd' in text or '(cid:' in text
            if not tables and needs_ocr and engine == 'paddle':
                from document_extract import inspect_page
                from paddle_extract import create_pipeline, enrich_document
                print(f'[INFO] Page {n+1}: sparse/unreadable text; starting optional OCR.',flush=True)
                pipeline = pipeline or create_pipeline()
                details = inspect_page(page)
                section = {'source_page': n+1, 'content': details['raw_text'], **details}
                result = enrich_document({'sections':[section]}, pdf_path, pipeline=pipeline, assets_dir=cache/'ocr')
                parser = TableParser()
                parser.feed(result['sections'][0]['ocr_markdown'])
                if parser.rows is not None:
                    raise ValueError(f'Incomplete OCR table on page {n+1}.')
                tables = [{'rows':rows,'merges':merges} for rows,merges in parser.tables]
                method = 'ocr'
                status = 'tables extracted; review OCR values' if tables else 'OCR found no structured tables; review page.'
            elif not tables and needs_ocr:
                status = 'Sparse/unreadable text: OCR may be needed. OCR is disabled.'
            record = {'source_page': n+1,'tables':tables,'method':method,'status':status}
            target = cache/f'page-{n+1}.json'
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
            replace_checkpoint(temporary, target)
        report.append({k:v for k,v in record.items() if k != 'tables'} | {'table_count':len(record['tables']), 'table_notes':[t['note'] for t in record['tables'] if 'note' in t]})
        if record['tables']:
            if fmt == 'csv':
                paths.extend(export_tables({'sections':[record]},output_dir,base_name,fmt))
            else:
                sections.append(record)
        elapsed = time.monotonic()-started
        eta = elapsed/index*(len(pages)-index)
        print(f'[INFO] Page {n+1} ({index}/{len(pages)}): {record["method"]}{" cached" if cached else ""}; {len(record["tables"])} tables; elapsed {elapsed:.1f}s; ETA ~{eta:.0f}s. {record["status"]}',flush=True)
        # A report survives cancellation along with completed page checkpoints/CSVs.
        report_path = destination/f'{base_name}_table_report.json'
        report_temp = report_path.with_suffix('.tmp')
        report_temp.write_text(json.dumps({'source':str(pdf_path),'requested_pages':len(pages),'completed_pages':index,'pages':report},ensure_ascii=False,indent=2),encoding='utf-8')
        replace_checkpoint(report_temp, report_path)
    if fmt == 'xlsx' and sections:
        paths = export_tables({'sections':sections},output_dir,base_name,fmt)
    if not paths:
        raise ValueError(f'No tables exported. See {report_path}. Enable optional OCR for scanned pages; digital borderless tables require review.')
    missing = sum(not p['table_count'] for p in report)
    print(f'[INFO] {len(pages)} pages completed; {missing} pages without detected tables. Native extraction preserves ruled bodies; separate or merged headers require review.', flush=True)
    print(f'[INFO] Review report: {report_path}',flush=True)
    return paths + [str(report_path)]
