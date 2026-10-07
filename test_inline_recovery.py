import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from inline_recovery import prepare_sections, recover_sections, render_section, merge_regions
from pdf_to_rag import build_markdown, process_pdf
from test_document_extract import write_pdf
from test_image_ocr import IMAGE, PROSE
import test_image_ocr as image_fixtures

class InlineRecoveryTests(unittest.TestCase):
    def test_markdown_places_recovered_table_between_native_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'mixed.pdf'
            write_pdf(path,PROSE+'\n'+IMAGE+'\nBT /F1 12 Tf 40 300 Td (Text resumes after the image.) Tj ET')
            pipeline=image_fixtures.ImageRecoveryTests().pipeline('<table><tr><td>Recovered middle table</td></tr></table>')
            with patch('paddle_extract.create_pipeline',return_value=pipeline):
                outputs=process_pdf(str(path),folder,output_format='both',engine='paddle')
            text=Path(next(p for p in outputs if p.endswith('.md'))).read_text(encoding='utf-8')
            self.assertLess(text.index('native paragraph'),text.index('Recovered middle table'))
            self.assertLess(text.index('Recovered middle table'),text.index('Text resumes'))
            self.assertEqual(text.count('Recovered middle table'),1)

    def test_consecutive_image_pages_end_when_native_text_resumes(self):
        sections=[]
        for n,images in [(1,True),(2,True),(3,False),(4,True)]:
            sections.append({'source_page':n,'raw_text':'Native readable text ' * 5,'content':'native', 'page_size':[612,792], 'image_regions':[[0,100,500,600]] if images else [],'source_lines':[]})
        prepare_sections(sections)
        self.assertEqual(sections[0]['ocr_flags'][0]['image_sequence'],sections[1]['ocr_flags'][0]['image_sequence'])
        self.assertFalse(sections[2]['ocr_flags'])
        self.assertNotEqual(sections[1]['ocr_flags'][0]['image_sequence'],sections[3]['ocr_flags'][0]['image_sequence'])

    def test_adjacent_tiles_join_but_separate_images_do_not(self):
        self.assertEqual(merge_regions([[0,100,100,200],[0,0,100,100],[200,0,300,100]]),[[0,0,100,200],[200,0,300,100]])

    def test_failure_leaves_visible_flag_and_continues(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'sample.pdf';write_pdf(pdf,PROSE)
            sections=[{'source_page':n,'content':'native','raw_text':'Readable native text '*4,'page_size':[612,792],'source_lines':[],'image_regions':[[0,0,100,100]],'warnings':[]} for n in [1,2]]
            def recover(section,*args):
                if section['source_page']==1:raise RuntimeError('test recognition failure')
                section['image_ocr']=[{'region':1,'markdown':'Recovered second image'}]
            with patch('paddle_extract.create_pipeline'),patch('image_ocr.enrich_images',side_effect=recover):
                recover_sections(sections,pdf,Path(folder)/'assets')
            self.assertIn('OCR UNRESOLVED',sections[0]['content'])
            self.assertIn('Recovered second image',sections[1]['content'])

    def test_partial_page_failure_keeps_completed_region_for_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'sample.pdf';write_pdf(pdf,PROSE)
            section={'source_page':1,'content':'native','raw_text':'Readable native text '*4,'page_size':[612,792],'source_lines':[], 'image_regions':[[0,0,100,100],[200,0,300,100]],'warnings':[]}
            def first(section,*args):
                section['image_ocr']=[{'region':1,'markdown':'First region recovered'}]
                raise RuntimeError('Second region failed')
            with patch('paddle_extract.create_pipeline'),patch('image_ocr.enrich_images',side_effect=first):
                recover_sections([section],pdf,Path(folder)/'assets')
            self.assertEqual([f['status'] for f in section['ocr_flags']],['converted','unresolved'])
            def retry(section,*args):
                self.assertEqual(section['image_ocr'][0]['markdown'],'First region recovered')
                section['image_ocr'][1]['markdown']='Second region recovered'
            with patch('paddle_extract.create_pipeline'),patch('image_ocr.enrich_images',side_effect=retry):
                recover_sections([section],pdf,Path(folder)/'assets')
            self.assertEqual([f['status'] for f in section['ocr_flags']],['converted','converted'])
