import csv
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from test_document_extract import write_pdf
from test_native_tables import GRID, TEXT
from document_extract import extract_document
from pdf_to_rag import process_pdf

IMAGE = 'q 100 0 0 100 40 400 cm BI /W 1 /H 1 /CS /RGB /BPC 8 /F /AHx ID FF0000> EI Q'
PROSE = 'BT /F1 12 Tf 40 740 Td (This native paragraph contains enough text to skip old OCR.) Tj ET'

class ImageRecoveryTests(unittest.TestCase):
    def pipeline(self, markdown):
        result = Mock()
        def predict(input):
            from PIL import Image
            with Image.open(input) as image:
                # A 100-point region at 300 DPI, including outward pixel rounding.
                self.assertTrue(all(416 <= side <= 418 for side in image.size))
            return [SimpleNamespace(json={'res':{}},markdown={'markdown_texts':markdown})]
        result.predict.side_effect=predict
        return result

    def test_mixed_json_keeps_native_and_recovers_image(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'mixed.pdf';write_pdf(pdf,PROSE+'\n'+IMAGE)
            self.assertEqual(extract_document(pdf)['sections'][0]['image_regions'],[[40.,400.,140.,500.]])
            pipeline=self.pipeline('Recovered image text 00123')
            with patch('paddle_extract.create_pipeline',return_value=pipeline):
                paths=process_pdf(str(pdf),folder,engine='paddle')
            section=json.loads(Path(paths[0]).read_text(encoding='utf-8'))['sections'][0]
            self.assertIn('native paragraph',section['content'])
            self.assertIn('Recovered image text 00123',section['content'])
            self.assertEqual(len(section['image_ocr']),1)
            pipeline.predict.assert_called_once()

    def test_native_table_does_not_hide_image_table_and_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'mixed.pdf';write_pdf(pdf,GRID+'\n'+TEXT+'\n'+IMAGE)
            pipeline=self.pipeline('<table><tr><td>image-001</td></tr></table>')
            with patch('paddle_extract.create_pipeline',return_value=pipeline):
                paths=process_pdf(str(pdf),folder,output_format='csv',engine='paddle')
            csvs=[p for p in paths if p.endswith('.csv')]
            self.assertEqual(len(csvs),1)
            with open(csvs[0],encoding='utf-8-sig',newline='') as stream:
                self.assertEqual(list(csv.reader(stream)),[['0012','A'],['0012','B'],['image-001']])
            with patch('paddle_extract.create_pipeline',side_effect=AssertionError('completed image must not repeat')):
                process_pdf(str(pdf),folder,output_format='csv',engine='paddle')

    def test_image_prose_saved_even_when_csv_has_no_tables(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'mixed.pdf';write_pdf(pdf,PROSE+'\n'+IMAGE)
            with patch('paddle_extract.create_pipeline',return_value=self.pipeline('Important image paragraph')):
                paths=process_pdf(str(pdf),folder,output_format='csv',engine='paddle')
            notes=[p for p in paths if p.endswith('.csv')]
            self.assertEqual(len(notes),1)
            self.assertIn('Important image paragraph',Path(notes[0]).read_text(encoding='utf-8'))
