import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock
import app_bootstrap as setup
from image_ocr import enrich_images


class AutoSetupTests(unittest.TestCase):
    def test_nvidia_detection_uses_cuda_identity_not_windows_gpu_number(self):
        result=SimpleNamespace(returncode=0,stdout='0, NVIDIA GeForce RTX 5070 Ti, GPU-abc, 12.0, 580.10, 16384\n',stderr='')
        with patch('app_bootstrap.subprocess.run',return_value=result):
            gpu=setup.detect_gpus()[0]
        self.assertEqual(gpu['uuid'],'GPU-abc')
        self.assertEqual(setup.cuda_channel(gpu),'cu129')
        self.assertEqual(setup.cuda_channel({'compute_capability':8.6}),'cu126')

    def test_default_two_gpu_workers_even_if_one_is_faster(self):
        reports={'cpu':{'ok':True},'gpu1':{'ok':True,'images_per_minute':20},'gpu2':{'ok':True,'images_per_minute':18}}
        self.assertEqual(setup.select_configuration({'name':'GPU'},reports)[:2],('gpu:0',2))

    def test_failed_two_worker_benchmark_explains_fallback(self):
        device,workers,note=setup.select_configuration({'name':'GPU'},{'gpu1':{'ok':True},'gpu2':{'ok':False}})
        self.assertEqual((device,workers),('gpu:0',1))
        self.assertIn('failed',note)

    def test_gpu_failure_does_not_silently_select_cpu(self):
        with self.assertRaisesRegex(RuntimeError,'NVIDIA OCR failed'):
            setup.select_configuration({'name':'GPU'},{'cpu':{'ok':True},'gpu1':{'ok':False},'gpu2':{'ok':False}})

    def test_fingerprint_changes_for_driver_and_hardware(self):
        self.assertNotEqual(setup.signature({'driver':'1'}),setup.signature({'driver':'2'}))

    def test_bad_driver_detection_not_reported_as_no_gpu(self):
        with patch('app_bootstrap.subprocess.run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='driver failed')):
            with self.assertRaisesRegex(RuntimeError,'CUDA hardware'):
                setup.detect_gpus()

    def test_prepared_crop_worker_never_opens_original_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            image=Path(folder)/'crop.png';image.write_bytes(b'fixture')
            section={'source_page':2,'content':'native','warnings':[],'image_regions':[[0,0,10,10]],'_prepared_images':{1:str(image)}}
            pipeline=Mock();pipeline.predict.return_value=[SimpleNamespace(json={},markdown={'markdown_texts':'recovered'})]
            with patch('image_ocr.prepare_images',side_effect=AssertionError('GPU worker should not render PDF')):
                enrich_images(section,'does-not-exist.pdf',pipeline,folder)
            pipeline.predict.assert_called_once_with(input=str(image))
            self.assertEqual(section['image_ocr'][0]['markdown'],'recovered')
