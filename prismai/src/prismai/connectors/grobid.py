"""GROBID connector: send PDF for full-text extraction, parse TEI XML."""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
from lxml import etree

logger = logging.getLogger(__name__)

_TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _parse_tei_sections(root: etree._Element) -> list[dict]:
    """Extract sections from TEI XML body."""
    sections: list[dict] = []
    body = root.find(".//tei:body", _TEI_NS)
    if body is None:
        return sections

    offset = 0
    for div in body.findall(".//tei:div", _TEI_NS):
        head = div.find("tei:head", _TEI_NS)
        title = (head.text or "").strip() if head is not None else ""

        paragraphs = []
        for p in div.findall("tei:p", _TEI_NS):
            text = etree.tostring(p, method="text", encoding="unicode").strip()
            if text:
                paragraphs.append(text)

        section_text = "\n".join(paragraphs)
        if section_text:
            page_attr = div.get("n", "0")
            try:
                page = int(page_attr)
            except ValueError:
                page = 0

            sections.append({
                "title": title,
                "page": page,
                "start": offset,
                "text": section_text,
            })
            offset += len(section_text) + 1

    return sections


def _count_pages(root: etree._Element) -> int:
    """Estimate number of pages from TEI surface elements."""
    surfaces = root.findall(".//tei:surface", _TEI_NS)
    if surfaces:
        return len(surfaces)
    pages = root.findall(".//{http://www.tei-c.org/ns/1.0}pb")
    return max(len(pages), 1)


async def extract_document(
    pdf_path: str,
    grobid_url: str = "http://localhost:8070",
    timeout: int = 120,
) -> dict:
    """Send PDF to GROBID, parse TEI XML, return structured result.

    Returns {"content_text": ..., "sections": [...], "n_pages": int}.
    """
    url = f"{grobid_url}/api/processFulltextDocument"

    async with httpx.AsyncClient(timeout=timeout) as client:
        with open(pdf_path, "rb") as f:
            resp = await client.post(
                url,
                files={"input": (Path(pdf_path).name, f, "application/pdf")},
            )
        resp.raise_for_status()

    tei_xml = resp.text
    root = etree.fromstring(tei_xml.encode("utf-8"))

    sections = _parse_tei_sections(root)
    content_text = "\n\n".join(s["text"] for s in sections)
    n_pages = _count_pages(root)

    return {
        "content_text": content_text,
        "sections": sections,
        "n_pages": n_pages,
    }
