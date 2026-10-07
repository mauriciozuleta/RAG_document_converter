import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path

from conversion_jobs import run_worker
from test_document_extract import write_pdf


class WorkerTests(unittest.TestCase):
    def test_native_worker_success_and_durable_log(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = Path(folder) / 'sample.pdf'
            write_pdf(pdf, 'BT /F1 12 Tf 40 700 Td (Worker test text) Tj ET')
            result = run_worker(dict(pdf_path=str(pdf), output_dir=folder), threading.Event(), lambda _: None)
            self.assertTrue(Path(result[0]).exists())
            self.assertTrue(list((Path(folder) / '.conversion_logs').glob('*.log')))

    def test_worker_failure_is_reported_without_killing_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'worker failed'):
                run_worker(dict(pdf_path=str(Path(folder) / 'missing.pdf'), output_dir=folder), threading.Event(), lambda _: None)
            log = next((Path(folder) / '.conversion_logs').glob('*.log'))
            self.assertIn('Traceback', log.read_text(encoding='utf-8'))

    def test_cancel_terminates_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            cancel = threading.Event()
            cancel.set()
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                run_worker(dict(pdf_path='unused.pdf', output_dir=folder), cancel, lambda _: None)

    def test_abrupt_worker_exit_leaves_parent_alive(self):
        with tempfile.TemporaryDirectory() as folder:
            worker = Path(folder) / 'conversion_worker.py'
            worker.write_text('import os\nos._exit(77)\n', encoding='utf-8')
            with patch('conversion_jobs.__file__', str(Path(folder) / 'conversion_jobs.py')):
                with self.assertRaisesRegex(RuntimeError, 'exit 77'):
                    run_worker(dict(pdf_path='unused.pdf', output_dir=folder), threading.Event(), lambda _: None)


if __name__ == '__main__':
    unittest.main()
