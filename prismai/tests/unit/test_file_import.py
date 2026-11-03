"""Unit tests for connectors/file_import.py — CSV, RIS, BibTeX parsing."""
from __future__ import annotations

from prismai.connectors.file_import import detect_and_parse, parse_csv


class TestCSV:
    def test_basic_csv(self):
        content = b"title,abstract,doi,year\nMy Paper,Some abstract,10.1234/a,2023\n"
        records = parse_csv(content)
        assert len(records) == 1
        assert records[0]["titulo"] == "My Paper"
        assert records[0]["abstract"] == "Some abstract"
        assert records[0]["doi"] == "10.1234/a"
        assert records[0]["year"] == 2023
        assert records[0]["source"] == "csv"

    def test_semicolon_separator(self):
        content = b"title;abstract;doi\nPaper A;Abstract A;10.1/a\nPaper B;Abstract B;10.1/b\n"
        records = parse_csv(content)
        assert len(records) == 2

    def test_missing_columns(self):
        content = b"name,description\nFoo,Bar\n"
        records = parse_csv(content)
        assert len(records) == 0

    def test_authors_split(self):
        content = b"title,abstract,authors\nPaper,Abs,Alice; Bob; Carol\n"
        records = parse_csv(content)
        assert records[0]["authors"] == ["Alice", "Bob", "Carol"]


class TestDetectAndParse:
    def test_csv_by_extension(self):
        content = b"title,abstract\nA,B\n"
        records, fmt = detect_and_parse(content, "refs.csv")
        assert fmt == "csv"
        assert len(records) == 1

    def test_ris_by_content(self):
        ris_content = (
            b"TY  - JOUR\n"
            b"TI  - Test Paper\n"
            b"AB  - Some abstract\n"
            b"DO  - 10.1234/test\n"
            b"AU  - Smith, John\n"
            b"PY  - 2023\n"
            b"ER  - \n"
        )
        records, fmt = detect_and_parse(ris_content, "unknown")
        assert fmt == "ris"
        assert len(records) == 1
        assert records[0]["titulo"] == "Test Paper"
        assert records[0]["doi"] == "10.1234/test"

    def test_bibtex_by_extension(self):
        bib_content = (
            b"@article{test2023,\n"
            b"  title = {Test Paper},\n"
            b"  author = {Smith, John},\n"
            b"  year = {2023},\n"
            b"  abstract = {Some abstract},\n"
            b"  doi = {10.1234/test},\n"
            b"}\n"
        )
        records, fmt = detect_and_parse(bib_content, "refs.bib")
        assert fmt == "bibtex"
        assert len(records) == 1
        assert records[0]["titulo"] == "Test Paper"
        assert records[0]["year"] == 2023
