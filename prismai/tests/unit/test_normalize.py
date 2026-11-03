from prismai.text.normalize import casa_termo, normalizar


class TestNormalizar:
    def test_remove_accents(self):
        assert normalizar("João") == "joao"

    def test_normalizes_whitespace(self):
        assert normalizar("  a  b  ") == "a b"

    def test_lowercases(self):
        assert normalizar("ABC") == "abc"

    def test_combined(self):
        assert normalizar("  Ação  Rápida  ") == "acao rapida"


class TestCasaTermo:
    def test_matches_word_start(self):
        assert casa_termo("um llm-based tutor", "llm") is True

    def test_rejects_mid_word_llm(self):
        assert casa_termo("enrollment", "llm") is False

    def test_rejects_mid_word_ia(self):
        assert casa_termo("tecnologia artificial", "ia") is False

    def test_accepts_word_start_prefix(self):
        assert casa_termo("profissionais de vendas", "profission") is True

    def test_accepts_exact_word(self):
        assert casa_termo("ia generativa", "ia") is True

    def test_rejects_absent_term(self):
        assert casa_termo("nada aqui", "llm") is False
