import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from memory_budget import capacity, worker_budget
from ocr_parallel import choose_workers

class MemoryBudgetTests(unittest.TestCase):
    def test_benchmark_does_not_spawn_when_memory_is_low(self):
        import app_bootstrap
        with tempfile.TemporaryDirectory() as folder:
            with patch('app_bootstrap.snapshot', return_value={'ram_gib': 7, 'vram_gib': 12}), patch('app_bootstrap.run_logged') as spawn:
                report = app_bootstrap.benchmark('python', 'gpu:0', 3, Path(folder), {})
                self.assertTrue(report['skipped_memory'])
                spawn.assert_not_called()

    def test_three_fit_with_sixteen_gib_free(self):
        self.assertEqual(capacity({'ram_gib':16, 'vram_gib':10}, worker_budget({})),3)

    def test_ram_and_vram_independently_limit(self):
        budget=worker_budget({})
        self.assertEqual(capacity({'ram_gib':9,'vram_gib':12},budget),2)
        self.assertEqual(capacity({'ram_gib':16,'vram_gib':6},budget),2)
        self.assertEqual(capacity({'ram_gib':4,'vram_gib':12},budget),0)

    def test_reserved_peak_and_growth_allowance(self):
        budget=worker_budget({'gpu1':{'ok':True,'results':[{'rss_bytes':4*1024**3,'peak_reserved_vram_bytes':3*1024**3}]}})
        self.assertEqual(budget['ram_per_worker_gib'],5)
        self.assertEqual(budget['vram_per_worker_gib'],3.75)

    def test_runtime_rechecks_memory_and_caps_selection(self):
        with patch.dict(os.environ, {'PDF_RAG_OCR_DEVICE':'gpu:0','PDF_RAG_MAX_WORKERS':'3','PDF_RAG_MEMORY_BUDGET':'{"ram_per_worker_gib":2.5,"vram_per_worker_gib":2.5}'}):
            with patch('memory_budget.snapshot',return_value={'ram_gib':9,'vram_gib':12}):
                self.assertEqual(choose_workers(3,595),2)
            with patch('memory_budget.snapshot',return_value={'ram_gib':4,'vram_gib':12}):
                with self.assertRaisesRegex(RuntimeError,'Insufficient'):
                    choose_workers(3,595)

    def test_three_gpu_workers_supported(self):
        with patch.dict(os.environ, {'PDF_RAG_OCR_DEVICE':'gpu:0'}, clear=True):
            self.assertEqual(choose_workers(3,595),3)
            self.assertEqual(choose_workers(3,2),2)
