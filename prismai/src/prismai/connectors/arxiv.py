from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def buscar_arxiv(query: str, max_results: int = 5) -> list[dict]:
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    url = f"https://export.arxiv.org/api/query?{params}"
    for tentativa in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "UNICAMP-INF0093/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_data = resp.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and tentativa < 2:
                time.sleep(5 * (tentativa + 1))
                continue
            return [{"erro": f"HTTP {e.code}: {e.reason}"}]
        except Exception as e:
            return [{"erro": f"HTTP: {type(e).__name__}: {e}"}]
    else:
        return [{"erro": "Esgotou tentativas (rate limit)."}]
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        return [{"erro": f"XML: {e}"}]
    ns = {"a": "http://www.w3.org/2005/Atom"}
    res: list[dict] = []
    for entry in root.findall("a:entry", ns):
        t = entry.find("a:title", ns)
        s = entry.find("a:summary", ns)
        i = entry.find("a:id", ns)
        titulo = t.text.strip().replace("\n", " ") if t is not None and t.text else ""
        abstract = s.text.strip().replace("\n", " ") if s is not None and s.text else ""
        aid = i.text.strip() if i is not None else ""
        if titulo and titulo.lower() != "error" and abstract:
            res.append({"id": aid, "titulo": titulo, "abstract": abstract})
    return res
