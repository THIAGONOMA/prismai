import re
import unicodedata


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def casa_termo(texto_norm: str, termo: str) -> bool:
    """Match term only at word start (suffix allowed). Avoids 'ia' inside 'tecnologia'."""
    return re.search(rf"(?<!\w){re.escape(termo)}", texto_norm) is not None
