"""Conservative, auditable extraction for arbitrary PDF layouts.

Source text and coordinates are authoritative. Reading order is a heuristic;
no values, headers, footnotes, or repeated lines are silently removed.
"""
from pathlib import Path
import re

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextLine, LTImage, LTLine, LTRect, LAParams


def walk(obj):
    yield obj
    if hasattr(obj, '__iter__'):
        for child in obj:
            yield from walk(child)


def inspect_page(page):
    objects = list(walk(page))
    lines = [obj for obj in objects if isinstance(obj, LTTextLine) and obj.get_text().strip()]
    source = [{'text': line.get_text().rstrip('\n'),
               'bbox': [round(v, 3) for v in line.bbox]} for line in lines]
    # A spatial view retains indentation and column separation. Use overlap
    # rather than baseline equality so superscripts stay beside their text.
    rows = []
    for line in sorted(lines, key=lambda obj: (-obj.y1, obj.x0)):
        target = next((row for row in reversed(rows[-3:])
                       if min(row['top'], line.y1) - max(row['bottom'], line.y0)
                       >= min(row['top'] - row['bottom'], line.height) * .5), None)
        if target is None:
            rows.append({'top': line.y1, 'bottom': line.y0, 'lines': [line]})
        else:
            target['lines'].append(line)
            target['top'] = max(target['top'], line.y1)
            target['bottom'] = min(target['bottom'], line.y0)
    visual = []
    for row in rows:
        text = ''
        for line in sorted(row['lines'], key=lambda obj: obj.x0):
            position = round(line.x0 / 4)
            text += ' ' * max(2 if text else 0, position - len(text)) + line.get_text().strip()
        visual.append(text)
    images = [obj for obj in objects if isinstance(obj, LTImage)]
    raw = '\n'.join(item['text'] for item in source)
    issues = []
    if not raw.strip():
        issues.append('No extractable text: page may be blank, scanned, or contain vector outlines; review/OCR required.')
    elif len(raw.strip()) < 40:
        issues.append('Sparse text: review page for missing content.')
    if images:
        issues.append('Embedded images are not transcribed; review figures and any text inside images.')
    if '\ufffd' in raw or re.search(r'\(cid:\d+\)', raw):
        issues.append('Unresolved font characters detected; review/OCR required.')
    if any(isinstance(obj, (LTLine, LTRect)) and max(obj.width, obj.height) > 50 for obj in objects):
        issues.append('Rules or vector graphics detected; table relationships and diagrams require review.')
    return {'source_lines': source, 'raw_text': raw,
            'layout_text': '\n'.join(visual), 'warnings': issues,
            'image_count': len(images), 'page_size': [page.width, page.height],
            'reading_order': 'PDF layout heuristic; coordinates retained for verification'}


def extract_document(path, page_numbers=None):
    selected = sorted(set(page_numbers)) if page_numbers is not None else None
    result = {'schema_version': 2, 'document_type': 'pdf', 'chapter': None,
              'title': Path(path).stem, 'source': Path(path).name,
              'extraction_method': 'pdfminer layout; no OCR', 'sections': []}
    for index, page in enumerate(extract_pages(path, page_numbers=selected,
                                              laparams=LAParams(detect_vertical=True, all_texts=True))):
        number = selected[index] + 1 if selected is not None else index + 1
        details = inspect_page(page)
        result['sections'].append({'id': f'page-{number}', 'title': f'PDF page {number}',
                                   'source_page': number, 'content': details['raw_text'],
                                   'tags': [], **details})
        if number % 100 == 0:
            print(f'[INFO] Extracted PDF page {number}', flush=True)
    result['review_required'] = any(s['warnings'] for s in result['sections'])
    return result
