"""Parsers for CSV, RIS, and BibTeX file import."""
from __future__ import annotations

import csv
import io
import logging

logger = logging.getLogger(__name__)

_CSV_FIELD_MAP: dict[str, str] = {
    "title": "titulo",
    "titulo": "titulo",
    "ti": "titulo",
    "abstract": "abstract",
    "ab": "abstract",
    "resumo": "abstract",
    "doi": "doi",
    "authors": "authors",
    "author": "authors",
    "au": "authors",
    "autores": "authors",
    "year": "year",
    "ano": "year",
    "py": "year",
    "publication_year": "year",
    "id": "id",
    "external_id": "id",
}


def parse_csv(content: bytes, encoding: str = "utf-8") -> list[dict]:
    text = content.decode(encoding, errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    col_map = _build_col_map(reader.fieldnames or [])

    results: list[dict] = []
    for row in reader:
        rec = _map_row(row, col_map)
        if rec.get("titulo") or rec.get("abstract"):
            results.append(rec)
    return results


def _build_col_map(fieldnames: list[str]) -> dict[str, str]:
    """Map actual CSV column names to canonical field names."""
    mapping: dict[str, str] = {}
    for col in fieldnames:
        key = col.strip().lower().replace(" ", "_")
        if key in _CSV_FIELD_MAP:
            mapping[col] = _CSV_FIELD_MAP[key]
    return mapping


def _map_row(row: dict, col_map: dict[str, str]) -> dict:
    rec: dict = {"id": "", "titulo": "", "abstract": "", "source": "csv"}
    for csv_col, field in col_map.items():
        val = (row.get(csv_col) or "").strip()
        if not val:
            continue
        if field == "authors":
            rec["authors"] = [a.strip() for a in val.replace(";", ",").split(",") if a.strip()]
        elif field == "year":
            try:
                rec["year"] = int(val)
            except ValueError:
                pass
        else:
            rec[field] = val
    if not rec.get("id"):
        rec["id"] = rec.get("doi") or rec.get("titulo", "")[:80]
    return rec


def parse_ris(content: bytes, encoding: str = "utf-8") -> list[dict]:
    import rispy

    text = content.decode(encoding, errors="replace")
    entries = rispy.load(io.StringIO(text))

    results: list[dict] = []
    for entry in entries:
        titulo = entry.get("title", entry.get("primary_title", ""))
        abstract = entry.get("abstract", entry.get("notes_abstract", ""))
        doi = entry.get("doi", "")
        authors = entry.get("first_authors", entry.get("authors", []))

        year = None
        raw_year = entry.get("year") or entry.get("publication_year", "")
        if raw_year:
            try:
                year = int(str(raw_year)[:4])
            except ValueError:
                pass

        rec = {
            "id": doi or entry.get("id", titulo[:80] if titulo else ""),
            "titulo": titulo,
            "abstract": abstract,
            "doi": doi or None,
            "authors": authors if isinstance(authors, list) else [authors],
            "year": year,
            "source": "ris",
        }
        if rec["titulo"] or rec["abstract"]:
            results.append(rec)

    return results


def parse_bibtex(content: bytes, encoding: str = "utf-8") -> list[dict]:
    from pybtex.database.input import bibtex as bibtex_input

    text = content.decode(encoding, errors="replace")
    parser = bibtex_input.Parser()
    bib_data = parser.parse_stream(io.StringIO(text))

    results: list[dict] = []
    for key, entry in bib_data.entries.items():
        fields = entry.fields
        titulo = fields.get("title", "")
        abstract = fields.get("abstract", "")
        doi = fields.get("doi", "") or None

        authors = []
        for person in entry.persons.get("author", []):
            parts = []
            if person.last_names:
                parts.append(" ".join(person.last_names))
            if person.first_names:
                parts.append(" ".join(person.first_names))
            if parts:
                authors.append(", ".join(parts))

        year = None
        raw_year = fields.get("year", "")
        if raw_year:
            try:
                year = int(str(raw_year)[:4])
            except ValueError:
                pass

        rec = {
            "id": doi or key,
            "titulo": titulo,
            "abstract": abstract,
            "doi": doi,
            "authors": authors,
            "year": year,
            "source": "bibtex",
        }
        if rec["titulo"] or rec["abstract"]:
            results.append(rec)

    return results


def detect_and_parse(content: bytes, filename: str, encoding: str = "utf-8") -> tuple[list[dict], str]:
    """Auto-detect file format and parse. Returns (records, format_name)."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "ris":
        return parse_ris(content, encoding), "ris"
    if ext in ("bib", "bibtex"):
        return parse_bibtex(content, encoding), "bibtex"
    if ext in ("csv", "tsv", "txt"):
        return parse_csv(content, encoding), "csv"

    text_preview = content[:512].decode(encoding, errors="replace")
    if text_preview.strip().startswith("TY  -"):
        return parse_ris(content, encoding), "ris"
    if text_preview.strip().startswith("@"):
        return parse_bibtex(content, encoding), "bibtex"

    return parse_csv(content, encoding), "csv"
