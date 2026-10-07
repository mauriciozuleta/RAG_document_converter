"""Local PaddleOCR PP-StructureV3 enrichment, retaining native PDF evidence."""
import json
import os
from pathlib import Path
import tempfile


def parse_pages(value):
    if not value.strip():
        return None
    pages = set()
    for part in value.split(','):
        bounds = part.strip().split('-')
        if len(bounds) > 2:
            raise ValueError('Pages must be numbers or ranges, such as 1-5,10.')
        start, end = int(bounds[0]), int(bounds[-1])
        if start < 1 or end < start:
            raise ValueError('Page numbers start at 1; ranges must be ascending.')
        pages.update(range(start - 1, end))
    return sorted(pages)


def create_pipeline():
    from paddleocr import PPStructureV3
    device = os.environ.get('PDF_RAG_OCR_DEVICE', 'cpu')
    if device not in ('cpu', 'gpu:0'):
        raise ValueError('OCR device must be cpu or gpu:0')
    if device.startswith('gpu'):
        import paddle
        if not paddle.is_compiled_with_cuda() or paddle.device.cuda.device_count() < 1:
            raise RuntimeError('GPU OCR requires the GPU environment and an available CUDA device.')
    print(f'[INFO] Loading OCR on {device}', flush=True)
    return PPStructureV3(device=device, use_doc_orientation_classify=True,
                         use_doc_unwarping=False, use_textline_orientation=True,
                         use_formula_recognition=False, use_chart_recognition=False,
                         use_seal_recognition=False, enable_mkldnn=False)


def enrich_document(data, pdf_path, pipeline=None, assets_dir=None):
    import pypdfium2 as pdfium
    print('[INFO] Loading local PaddleOCR layout/table models ...', flush=True)
    pipeline = pipeline or create_pipeline()
    with pdfium.PdfDocument(pdf_path) as pdf, tempfile.TemporaryDirectory(prefix='pdf_rag_ocr_') as folder:
        for section in data['sections']:
            number = section['source_page']
            print(f'[INFO] OCR and table recognition: PDF page {number}', flush=True)
            page = pdf[number - 1]
            try:
                bitmap = page.render(scale=2.5)
                try:
                    image = bitmap.to_pil()
                    path = Path(folder) / 'page.png'
                    image.save(path)
                    image.close()
                finally:
                    bitmap.close()
            finally:
                page.close()
            predictions = list(pipeline.predict(input=str(path)))
            if len(predictions) != 1:
                raise RuntimeError(f'Expected one OCR result for PDF page {number}, got {len(predictions)}.')
            prediction = predictions[0]
            raw = prediction.json
            if isinstance(raw, str):
                raw = json.loads(raw)
            md_info = prediction.markdown
            markdown = md_info.get('markdown_texts', '')
            if not isinstance(markdown, str):
                raise RuntimeError('PaddleOCR returned an unsupported Markdown format.')
            for name, image in md_info.get('markdown_images', {}).items():
                if assets_dir is None:
                    continue
                destination = Path(assets_dir) / f'page-{number}' / Path(name).name
                destination.parent.mkdir(parents=True, exist_ok=True)
                image.save(destination)
                relative = Path(assets_dir).name + f'/page-{number}/' + destination.name
                markdown = markdown.replace(name, relative)
            section['native_content'] = section['content']
            section['native_warnings'] = list(section['warnings'])
            section['warnings'] = ['Native PDF extraction: ' + warning for warning in section['warnings']]
            section['ocr_result'] = raw
            section['ocr_markdown'] = markdown
            section['ocr_render_scale'] = 2.5
            section['ocr_coordinate_system'] = 'Rendered image pixels, top-left origin; native PDF coordinates retained separately.'
            section['content'] = markdown or section['native_content']
            section['warnings'].append('OCR/table structure is model-derived; compare critical values with retained native text or original page. Formula, chart, and seal recognition are disabled.')
            if not markdown.strip():
                section['warnings'].append('OCR produced no Markdown; native content retained.')
    data['extraction_method'] = 'Native PDF evidence plus local PaddleOCR PP-StructureV3 (CPU)'
    data['review_required'] = True
    return data
