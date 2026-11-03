"""Unit tests for connectors/grobid.py — TEI XML parsing."""
from __future__ import annotations

from lxml import etree

from prismai.connectors.grobid import _count_pages, _parse_tei_sections

_TEI_XML = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader/>
  <text>
    <body>
      <div n="1">
        <head>Introduction</head>
        <p>This study investigates the effects of treatment X.</p>
      </div>
      <div n="3">
        <head>Methods</head>
        <p>We conducted a randomized controlled trial with 200 participants.</p>
      </div>
    </body>
  </text>
</TEI>"""


def test_parse_tei_sections():
    root = etree.fromstring(_TEI_XML.encode("utf-8"))
    sections = _parse_tei_sections(root)
    assert len(sections) == 2
    assert sections[0]["title"] == "Introduction"
    assert sections[1]["title"] == "Methods"
    assert "treatment X" in sections[0]["text"]
    assert sections[1]["page"] == 3


def test_count_pages():
    root = etree.fromstring(_TEI_XML.encode("utf-8"))
    n = _count_pages(root)
    assert n >= 1
