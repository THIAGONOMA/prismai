"""OCR confidence estimator using PyMuPDF."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_MIN_CHARS_PER_PAGE = 200


def estimate_ocr_confidence(pdf_path: str) -> float:
    """Estimate text extraction quality.

    Returns a 0-1 score where low values indicate scanned PDFs without OCR.
    Heuristic: ratio of pages with sufficient text to total pages.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed; assuming OCR confidence = 1.0")
        return 1.0

    try:
        doc = fitz.open(pdf_path)
        n_pages = len(doc)
        if n_pages == 0:
            return 0.0

        pages_with_text = 0
        for page in doc:
            text = page.get_text()
            if len(text.strip()) >= _MIN_CHARS_PER_PAGE:
                pages_with_text += 1

        doc.close()
        return pages_with_text / n_pages
    except Exception as e:
        logger.warning("OCR confidence estimation failed for %s: %s", pdf_path, e)
        return 0.0
