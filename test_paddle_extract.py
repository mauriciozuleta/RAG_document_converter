import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from document_extract import extract_document
from paddle_extract import parse_pages, enrich_document
from pdf_to_rag import build_markdown
from test_document_extract import write_pdf


class PaddleTests(unittest.TestCase):
    def test_page_ranges(self):
        self.assertEqual(parse_pages('1,3-5,3'), [0, 2, 3, 4])
        self.assertIsNone(parse_pages(''))
        for invalid in ['0', '5-1', '1-2-3', 'abc']:
            with self.assertRaises(ValueError):
                parse_pages(invalid)

    def test_ocr_keeps_native_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sample.pdf'
            write_pdf(path, 'BT /F1 12 Tf 40 700 Td (Native 0101) Tj ET')
            data = extract_document(path)
            prediction = SimpleNamespace(json={'res': {'parsing_res_list': []}},
                                         markdown={'markdown_texts': '<table><tr><td>0101</td></tr></table>'})
            pipeline = Mock()
            pipeline.predict.return_value = [prediction]
            assets = Path(folder) / 'assets'
            enrich_document(data, path, pipeline=pipeline, assets_dir=assets)
            section = data['sections'][0]
            self.assertIn('Native 0101', section['native_content'])
            self.assertIn('Native 0101', section['raw_text'])
            self.assertIn('<table>', section['content'])
            self.assertNotIn('ocr_result', section)
            self.assertTrue((assets / 'page-1' / 'ocr_result.json').exists())
            self.assertTrue((assets / 'page-1' / 'page.md').exists())
            md = build_markdown(data)
            self.assertIn('<table>', md)
            self.assertIn('Native 0101', md)


if __name__ == '__main__':
    unittest.main()
