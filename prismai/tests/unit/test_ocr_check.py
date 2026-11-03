"""Unit tests for connectors/ocr_check.py."""
from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch


def test_estimate_ocr_confidence_good_pdf():
    mock_page = MagicMock()
    mock_page.get_text.return_value = "A" * 300

    mock_doc = MagicMock()
    mock_doc.__len__ = MagicMock(return_value=2)
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page, mock_page]))
    mock_doc.close = MagicMock()

    mock_fitz = MagicMock()
    mock_fitz.open.return_value = mock_doc

    with patch.dict("sys.modules", {"fitz": mock_fitz}):
        import prismai.connectors.ocr_check as mod
        importlib.reload(mod)
        conf = mod.estimate_ocr_confidence("/fake/path.pdf")
        assert conf == 1.0


def test_estimate_ocr_confidence_scanned_pdf():
    mock_page = MagicMock()
    mock_page.get_text.return_value = "AB"

    mock_doc = MagicMock()
    mock_doc.__len__ = MagicMock(return_value=5)
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page] * 5))
    mock_doc.close = MagicMock()

    mock_fitz = MagicMock()
    mock_fitz.open.return_value = mock_doc

    with patch.dict("sys.modules", {"fitz": mock_fitz}):
        import prismai.connectors.ocr_check as mod
        importlib.reload(mod)
        conf = mod.estimate_ocr_confidence("/fake/scan.pdf")
        assert conf == 0.0
