"""Versioned OCR policy; changes invalidate recovered-image checkpoints."""
import os

RENDER_SCALE = 300 / 72


def pipeline_options():
    return dict(text_recognition_model_name=os.environ.get('PDF_RAG_OCR_MODEL', 'en_PP-OCRv5_mobile_rec'),
                text_det_thresh=0.2, text_det_box_thresh=0.3,
                text_det_unclip_ratio=1.2, markdown_ignore_labels=[])


def cache_policy():
    return ['inline-v2-accuracy', RENDER_SCALE, pipeline_options(), os.environ.get('PDF_RAG_OCR_DEVICE', 'cpu')]
