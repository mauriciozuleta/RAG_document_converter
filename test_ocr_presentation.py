import unittest
from ocr_presentation import readable_markdown, quality_warnings


class PresentationTests(unittest.TestCase):
    def test_table_keeps_first_data_row_and_escapes_pipes(self):
        text = readable_markdown('<div><html><body><table><tr><td>001</td><td>a|b</td></tr><tr><td>002</td><td>c</td></tr></table></body></html></div>')
        self.assertIn('| 001 | a\\|b |', text)
        self.assertIn('| 002 | c |', text)
        self.assertNotIn('<html>', text)

    def test_merged_cells_retain_html_structure(self):
        text = readable_markdown('<table><tr><td colspan="2">heading</td></tr></table>')
        self.assertIn('colspan="2"', text)

    def test_flags_do_not_rewrite_recognition(self):
        text = 'Dairyproducebirdseggsnaturalhoney cm^{$'
        concerns = quality_warnings({'res': {'overall_ocr_res': {'rec_scores': [.82]}}}, text)
        self.assertEqual(len(concerns), 3)
        self.assertEqual(readable_markdown(text), text)

    def test_good_confidence_is_not_an_accuracy_certificate(self):
        self.assertEqual(quality_warnings({'res': {'overall_ocr_res': {'rec_scores': [.99]}}}, 'Sample text'), [])

    def test_model_change_invalidates_recovery_cache(self):
        import os
        from unittest.mock import patch
        from inline_recovery import recovery_cache_path
        section = {'source_page': 1, 'image_regions': [[0, 0, 10, 10]]}
        before = recovery_cache_path(section, 'assets', 'digest')
        with patch.dict(os.environ, {'PDF_RAG_OCR_MODEL': 'PP-OCRv5_server_rec'}):
            self.assertNotEqual(before, recovery_cache_path(section, 'assets', 'digest'))

    def test_cudnn_repair_is_verified_and_scoped_to_matching_build(self):
        from unittest.mock import patch
        from pathlib import Path
        from app_bootstrap import repair_cudnn
        with patch('app_bootstrap.run_logged') as install, patch('app_bootstrap.probe', return_value={'cudnn_package': '9.9.0.52'}):
            repair_cudnn(Path('python.exe'), 'gpu:0', {'cudnn_build': '9.9.0', 'cudnn_package': '9.5.1.17'}, {})
            self.assertIn('nvidia-cudnn-cu12==9.9.0.52', install.call_args.args[0])
        with patch('app_bootstrap.run_logged') as install:
            repair_cudnn(Path('python.exe'), 'gpu:0', {'cudnn_build': '9.13.0'}, {})
            install.assert_not_called()
