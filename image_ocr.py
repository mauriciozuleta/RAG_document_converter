"""Recover text/table content from embedded image regions on mixed PDF pages."""
import json
from pathlib import Path
import tempfile


def enrich_images(section, pdf_path, pipeline, assets_dir):
    import pypdfium2 as pdfium
    number = section['source_page']
    destination = Path(assets_dir) / f'page-{number}' / 'images'
    destination.mkdir(parents=True, exist_ok=True)
    completed = {r["region"]:r for r in section.get("image_ocr", []) if r.get("markdown", "").strip()}
    results = []
    section["image_ocr"] = results
    with pdfium.PdfDocument(pdf_path) as pdf, tempfile.TemporaryDirectory(prefix='pdf_image_ocr_') as temporary:
        page = pdf[number - 1]
        try:
            width, height = page.get_size()
            bitmap = page.render(scale=2.5)
            try:
                rendered = bitmap.to_pil()
                try:
                    for index, bbox in enumerate(section.get('image_regions', []), 1):
                        if index in completed:
                            results.append(completed[index])
                            continue
                        x0, y0, x1, y1 = bbox
                        sx, sy = rendered.width / width, rendered.height / height
                        crop_box = (max(0, int(x0*sx)), max(0, int((height-y1)*sy)),
                                    min(rendered.width, int(x1*sx + .999)), min(rendered.height, int((height-y0)*sy + .999)))
                        if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
                            results.append({'region': index, 'bbox': bbox, 'markdown': '', 'status': 'Invalid/clipped image region; review required.'})
                            continue
                        offset, total = section.get('_ocr_progress', (0, len(section['image_regions'])))
                        print(f'[INFO] OCR section {offset + index} of {total}: page {number}, image {index}; {total - offset - index + 1} remaining including this section.', flush=True)
                        crop = rendered.crop(crop_box)
                        path = Path(temporary) / 'image.png'
                        try:
                            crop.save(path)
                        finally:
                            crop.close()
                        predictions = list(pipeline.predict(input=str(path)))
                        if len(predictions) != 1:
                            raise RuntimeError(f'Expected one result for page {number}, image {index}.')
                        prediction = predictions[0]
                        raw = prediction.json
                        if isinstance(raw, str):
                            raw = json.loads(raw)
                        info = prediction.markdown
                        markdown = info.get('markdown_texts', '')
                        if not isinstance(markdown, str):
                            raise RuntimeError('Unsupported image OCR Markdown format.')
                        # Keep model image references local to the durable region artifact.
                        region_dir = destination / str(index)
                        region_dir.mkdir(exist_ok=True)
                        for name, image in info.get('markdown_images', {}).items():
                            target = region_dir / Path(name).name
                            image.save(target)
                            markdown = markdown.replace(name, target.resolve().as_posix())
                        (region_dir / 'ocr_result.json').write_text(json.dumps(raw, ensure_ascii=False), encoding='utf-8')
                        (region_dir / 'content.md').write_text(markdown, encoding='utf-8')
                        results.append({'region': index, 'bbox': bbox, 'markdown': markdown,
                                        'status': 'OCR completed; review accuracy.' if markdown.strip() else 'No text recognized; review image.',
                                        'artifact': str(region_dir / 'content.md')})
                finally:
                    rendered.close()
            finally:
                bitmap.close()
        finally:
            page.close()
    section['image_ocr'] = results
    recovered = '\n\n'.join(f'### Image {r["region"]}\n\n{r["markdown"]}' for r in results)
    section['image_ocr_markdown'] = recovered
    section['native_content'] = section['content']
    section['content'] += '\n\n## OCR of embedded images\n\n' + recovered
    section['warnings'].append('Embedded images processed with OCR; native text retained. Review images with no recognized text and model-derived values.')
    return section
