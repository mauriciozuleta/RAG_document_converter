import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_document_extract import write_pdf
from pdf_to_rag import process_pdf

GRID = '\n'.join([f'{x} 600 m {x} 700 l S' for x in [40,140,240]] + [f'40 {y} m 240 {y} l S' for y in [600,650,700]])
TEXT = '\n'.join(f'BT /F1 10 Tf {x} {y} Td ({value}) Tj ET' for x,y,value in [(45,680,'0012'),(145,680,'A'),(45,630,'0012'),(145,630,'B')])

class NativeTableTests(unittest.TestCase):
    def test_native_even_with_ocr_enabled_and_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'table.pdf'
            write_pdf(pdf,GRID+'\n'+TEXT)
            with patch('paddle_extract.create_pipeline',side_effect=AssertionError('OCR must not load')):
                paths=process_pdf(str(pdf),folder,output_format='csv',engine='paddle')
            with open(paths[0],encoding='utf-8-sig',newline='') as f:
                self.assertEqual(list(csv.reader(f)),[['0012','A'],['0012','B']])
            with patch('table_conversion.extract_pages',side_effect=AssertionError('Cached pages must not parse')):
                process_pdf(str(pdf),folder,output_format='csv',engine='paddle')
            # A changed source must not reuse the original checkpoint.
            write_pdf(pdf,GRID+'\n'+TEXT.replace('0012','0013'))
            paths=process_pdf(str(pdf),folder,output_format='csv',engine='paddle')
            with open(paths[0],encoding='utf-8-sig',newline='') as f:
                self.assertEqual(list(csv.reader(f))[0][0],'0013')

    def test_sparse_page_ocr_is_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'blank.pdf';write_pdf(pdf,'')
            with patch('paddle_extract.create_pipeline',side_effect=AssertionError('OCR disabled')):
                paths=process_pdf(str(pdf),folder,output_format='csv')
                self.assertIn('OCR PENDING',Path(paths[0]).read_text(encoding='utf-8-sig'))
            report=json.loads((Path(folder)/'blank_tables_table_report.json').read_text())
            self.assertEqual(report['pages'][0]['ocr_flags'][0]['status'],'pending')

    def test_optional_ocr_for_sparse_page(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'scan.pdf';write_pdf(pdf,'')
            def enrich(section,*args,**kwargs):
                section['image_ocr']=[{'region':1,'markdown':'<table><tr><td>001</td></tr></table>'}]
                return section
            with patch('paddle_extract.create_pipeline') as create, patch('image_ocr.enrich_images',side_effect=enrich):
                paths=process_pdf(str(pdf),folder,output_format='csv',engine='paddle')
                create.assert_called_once()
            self.assertTrue(Path(paths[0]).exists())

    def test_digital_prose_is_not_forced_through_ocr(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'prose.pdf';write_pdf(pdf,'BT /F1 10 Tf 40 700 Td (This is a digital page with ordinary prose and no table grid.) Tj ET')
            with patch('paddle_extract.create_pipeline',side_effect=AssertionError('Digital prose must not OCR')):
                with self.assertRaisesRegex(ValueError,'No tables exported'):
                    process_pdf(str(pdf),folder,output_format='csv',engine='paddle')
                process_pdf(str(pdf),folder,output_format='json',engine='paddle')

    def test_out_of_range_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'table.pdf';write_pdf(pdf,GRID+'\n'+TEXT)
            with self.assertRaisesRegex(ValueError,'page range'):
                process_pdf(str(pdf),folder,output_format='csv',pages='2')
            self.assertFalse(list(Path(folder).glob('*.csv')))
