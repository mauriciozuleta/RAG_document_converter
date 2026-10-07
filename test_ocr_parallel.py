import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from ocr_parallel import bounded_results, choose_workers
from inline_recovery import recover_sections


def scheduling_job(number):
    time.sleep(.15)
    if number == 2:
        raise ValueError('test failure')
    return number, os.getpid()


class ParallelOCRTests(unittest.TestCase):
    def test_spawned_workers_complete_jobs_and_surface_errors(self):
        with ProcessPoolExecutor(max_workers=2,mp_context=get_context('spawn')) as executor:
            results=list(bounded_results(executor,scheduling_job,[(i,) for i in range(6)],2))
        self.assertEqual(sorted(i for i,_,_ in results),list(range(6)))
        self.assertEqual(sum(error is not None for _,_,error in results),1)
        self.assertEqual(len({result[1] for _,result,error in results if error is None}),2)

    def test_memory_guard(self):
        with patch('ocr_parallel.os.cpu_count',return_value=20):
            with patch('ocr_parallel.available_memory_gb',return_value=8):
                self.assertEqual(choose_workers(2,100),1)
            with patch('ocr_parallel.available_memory_gb',return_value=16):
                self.assertEqual(choose_workers(2,100),2)
                self.assertEqual(choose_workers(2,1),1)

    def test_parallel_cached_recovery_preserves_original_page_order(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf=Path(folder)/'source.pdf';pdf.write_bytes(b'cache-test-source')
            digest=hashlib.sha256(pdf.read_bytes()).hexdigest()
            assets=Path(folder)/'assets'
            regions=[[0,0,100,100]]
            key=hashlib.sha256(json.dumps([digest,regions,'inline-v1']).encode()).hexdigest()[:24]
            sections=[]
            for page in range(1,5):
                checkpoint=assets/f'page-{page}'/f'recovery-{key}.json'
                checkpoint.parent.mkdir(parents=True)
                checkpoint.write_text(json.dumps([{'region':1,'markdown':f'Recovered page {page}'}]))
                sections.append({'source_page':page,'raw_text':'native '*10,'content':'native','warnings':[],'source_lines':[], 'image_regions':regions,'page_size':[612,792]})
            with patch('ocr_parallel.choose_workers',return_value=2):
                recover_sections(sections,pdf,assets,workers=2)
            self.assertEqual([s['source_page'] for s in sections],[1,2,3,4])
            self.assertTrue(all(f'Recovered page {i}' in section['content'] for i,section in enumerate(sections,1)))
            self.assertTrue(all(section['ocr_flags'][0]['status']=='converted' for section in sections))

    def test_gpu_always_uses_one_worker(self):
        with patch.dict(os.environ, {'PDF_RAG_OCR_DEVICE':'gpu:0'}):
            self.assertEqual(choose_workers(2,100),1)

    def test_gpu_factory_refuses_cpu_only_installation(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import Mock
        from paddle_extract import create_pipeline
        factory=Mock()
        with patch.dict(os.environ, {'PDF_RAG_OCR_DEVICE':'gpu:0'}), patch.dict(sys.modules, {'paddleocr':SimpleNamespace(PPStructureV3=factory), 'paddle':SimpleNamespace(is_compiled_with_cuda=lambda:False)}):
            with self.assertRaisesRegex(RuntimeError,'GPU OCR requires'):
                create_pipeline()
        factory.assert_not_called()
