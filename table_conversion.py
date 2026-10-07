"""Two-pass table export: native checkpoints, then inline flagged OCR recovery."""
import hashlib
import json
from pathlib import Path
import time
from pdfminer.high_level import extract_pages
from pdfminer.pdfpage import PDFPage
from native_tables import extract_grids
from table_export import export_tables, TableParser
from document_extract import inspect_page
from inline_recovery import recover_sections


def replace_checkpoint(temporary, target):
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
    cache = destination / '.table_checkpoints' / f'{digest[:20]}-v3-inline'
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
    sections = []
    for index,n in enumerate(pages,1):
        if n in stored:
            record = stored.pop(n)
        else:
            page = next(layouts)
            tables, text = extract_grids(page)
            details = inspect_page(page)
            record = {'source_page':n+1,'native_tables':tables,'content':details['raw_text'],**details}
            target = cache/f'page-{n+1}.json'
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
            replace_checkpoint(temporary,target)
        sections.append(record)
        elapsed = time.monotonic()-started
        print(f'[INFO] Native pass {index}/{len(pages)} (PDF page {n+1}); elapsed {elapsed:.1f}s; ETA ~{elapsed/index*(len(pages)-index):.0f}s',flush=True)
    if hasattr(layouts, 'close'):
        layouts.close()
    # Every selected page is inspected before any OCR model is loaded.
    recover_sections(sections,pdf_path,cache/'recovery',enabled=engine=='paddle')
    report, exported, paths = [], [], []
    for section in sections:
        number = section['source_page']
        blocks = [(t['bbox'],t['rows'],t.get('merges',[])) for t in section['native_tables']]
        for index,flag in enumerate(section.get('ocr_flags',[]),1):
            result = next((r for r in section.get('image_ocr',[]) if r['region']==index),None)
            if result and result.get('markdown','').strip():
                parser = TableParser()
                parser.feed(result['markdown'])
                # Preserve surrounding OCR prose as well as structured cells.
                if parser.tables and parser.rows is None:
                    import re
                    rows,merges = [],[]
                    for fragment in re.split(r'(<table\b.*?</table>)', result['markdown'], flags=re.I|re.S):
                        if not fragment.strip():
                            continue
                        fragment_parser = TableParser()
                        fragment_parser.feed(fragment)
                        if fragment_parser.tables:
                            for table_rows,table_merges in fragment_parser.tables:
                                offset=len(rows)
                                rows.extend(table_rows)
                                merges.extend((a+offset,b,c+offset,d) for a,b,c,d in table_merges)
                        else:
                            rows.append([fragment.strip()])
                else:
                    rows,merges = [[result['markdown']]],[]
                blocks.append((flag['bbox'],rows,merges))
            else:
                blocks.append((flag['bbox'],[[f'[OCR {flag["status"].upper()}: {flag["id"]} — image content requires review]']],[]))
        blocks.sort(key=lambda b:(-b[0][3],b[0][0]))
        rows,merges = [],[]
        for bbox,block_rows,block_merges in blocks:
            offset=len(rows)
            rows.extend(block_rows)
            merges.extend((a+offset,b,c+offset,d) for a,b,c,d in block_merges)
        if rows:
            record={'source_page':number,'tables':[{'rows':rows,'merges':merges}]}
            if fmt=='csv':
                paths.extend(export_tables({'sections':[record]},output_dir,base_name,fmt))
            else:
                exported.append(record)
        flags=section.get('ocr_flags',[])
        status = 'Native tables and image recovery in page order.' if rows else 'No ruled table detected; review digital/borderless content.'
        report.append({'source_page':number,'status':status,'ocr_flags':flags,'native_table_count':len(section['native_tables'])})
    if fmt=='xlsx' and exported:
        paths.extend(export_tables({'sections':exported},output_dir,base_name,fmt))
    report_path=destination/f'{base_name}_table_report.json'
    report_path.write_text(json.dumps({'source':str(pdf_path),'completed_pages':len(pages),'pages':report},ensure_ascii=False,indent=2),encoding='utf-8')
    if not paths:
        raise ValueError(f'No tables exported. See {report_path}.')
    return paths+[str(report_path)]
