"""CPU crop preparation and OCR of flagged image regions."""
import json
from pathlib import Path
import tempfile


def prepare_images(section, pdf_path, folder):
    """Render once on CPU; workers receive crop paths, not PDF contents."""
    import pypdfium2 as pdfium
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    completed={r['region'] for r in section.get('image_ocr',[]) if r.get('markdown','').strip()}
    paths={}
    if len(completed)==len(section.get('image_regions',[])):
        return paths
    with pdfium.PdfDocument(pdf_path) as pdf:
        page=pdf[section['source_page']-1]
        try:
            width,height=page.get_size()
            from ocr_settings import RENDER_SCALE
            rotation = section.get('orientation_correction', 0)
            bitmap=page.render(scale=RENDER_SCALE, rotation=rotation)
            if rotation in (90, 270):
                width, height = height, width
            try:
                rendered=bitmap.to_pil()
                try:
                    for index,(x0,y0,x1,y1) in enumerate(section.get('image_regions',[]),1):
                        if index in completed:
                            continue
                        sx,sy=rendered.width/width,rendered.height/height
                        box=(max(0,int(x0*sx)),max(0,int((height-y1)*sy)),min(rendered.width,int(x1*sx+.999)),min(rendered.height,int((height-y0)*sy+.999)))
                        if box[2]<=box[0] or box[3]<=box[1]:
                            paths[index]=None
                            continue
                        crop=rendered.crop(box)
                        try:
                            path=folder/f'image-{index}.png';crop.save(path);paths[index]=str(path)
                        finally:
                            crop.close()
                finally:
                    rendered.close()
            finally:
                bitmap.close()
        finally:
            page.close()
    return paths


def enrich_images(section, pdf_path, pipeline, assets_dir):
    number=section['source_page']
    destination=Path(assets_dir)/f'page-{number}'/'images'
    destination.mkdir(parents=True,exist_ok=True)
    completed={r['region']:r for r in section.get('image_ocr',[]) if r.get('markdown','').strip()}
    results=[]
    # Keep partial successes visible to recovery if a later region fails.
    with tempfile.TemporaryDirectory(prefix='pdf_image_ocr_') as temporary:
        paths=section.get('_prepared_images')
        if paths is None:
            paths=prepare_images(section,pdf_path,temporary)
        section['image_ocr']=results
        for index,bbox in enumerate(section.get('image_regions',[]),1):
            if index in completed:
                results.append(completed[index]);continue
            path=paths.get(index)
            if not path:
                results.append({'region':index,'bbox':bbox,'markdown':'','status':'Invalid/clipped image region; review required.'});continue
            offset,total=section.get('_ocr_progress',(0,len(section['image_regions'])))
            print(f'[INFO] OCR section {offset+index} of {total}: page {number}, image {index}; {total-offset-index+1} remaining including this section.',flush=True)
            predictions=list(pipeline.predict(input=str(path)))
            if len(predictions)!=1:
                raise RuntimeError(f'Expected one result for page {number}, image {index}.')
            prediction=predictions[0];raw=prediction.json
            if isinstance(raw,str):raw=json.loads(raw)
            info=prediction.markdown;markdown=info.get('markdown_texts','')
            if not isinstance(markdown,str):raise RuntimeError('Unsupported image OCR Markdown format.')
            from ocr_presentation import quality_warnings
            concerns = quality_warnings(raw, markdown)
            for concern in concerns:
                section.setdefault('warnings', []).append(f'Image {index}: {concern}')
            region_dir=destination/str(index);region_dir.mkdir(exist_ok=True)
            for name,image in info.get('markdown_images',{}).items():
                target=region_dir/Path(name).name;image.save(target)
                markdown=markdown.replace(name,target.resolve().as_posix())
            (region_dir/'ocr_result.json').write_text(json.dumps(raw,ensure_ascii=False),encoding='utf-8')
            (region_dir/'content.md').write_text(markdown,encoding='utf-8')
            results.append({'region':index,'bbox':bbox,'markdown':markdown,'accuracy_verified':False,'quality_warnings':concerns,'status':'OCR completed; review accuracy.' if markdown.strip() else 'No text recognized; review image.','artifact':str(region_dir/'content.md')})
    recovered='\n\n'.join(f'### Image {r["region"]}\n\n{r["markdown"]}' for r in results)
    section['image_ocr_markdown']=recovered
    section['native_content']=section['content']
    section['content']+='\n\n## OCR of embedded images\n\n'+recovered
    section['warnings'].append('Embedded images processed with OCR; native text retained. Review images with no recognized text and model-derived values.')
    return section
