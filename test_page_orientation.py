import tempfile
import unittest
from pathlib import Path
from test_document_extract import write_pdf
from document_extract import extract_document

class OrientationTests(unittest.TestCase):
    def test_native_rotations_preserve_text_and_order(self):
        for angle,matrix in [(0,'1 0 0 1 0 0'),(90,'0 1 -1 0 612 0'),(180,'-1 0 0 -1 612 792'),(270,'0 -1 1 0 0 792')]:
            with self.subTest(angle=angle), tempfile.TemporaryDirectory() as folder:
                p=Path(folder)/'sample.pdf'
                write_pdf(p, f'q {matrix} cm BT /F1 12 Tf 40 400 Td (First native line with tariff 00123) Tj 0 -25 Td (Second native line with duty 25 percent) Tj ET Q')
                s=extract_document(p)['sections'][0]
                self.assertEqual(s['orientation_correction'],angle)
                self.assertIn('00123',s['raw_text'])
                self.assertLess(s['layout_text'].index('First'),s['layout_text'].index('Second'))
