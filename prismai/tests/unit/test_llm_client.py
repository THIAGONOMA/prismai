from unittest.mock import MagicMock, patch


class TestCriarLlm:
    @patch("langchain_openai.ChatOpenAI", autospec=True)
    def test_openai_model_routes_to_chatopenai(self, mock_cls):
        from importlib import reload

        import prismai.llm.client as mod

        reload(mod)
        mock_cls.return_value = MagicMock()
        result = mod.criar_llm(model="gpt-4o-mini")
        mock_cls.assert_called_once_with(model="gpt-4o-mini", temperature=0, timeout=60, max_retries=0)
        assert result is mock_cls.return_value

    @patch("langchain_anthropic.ChatAnthropic", autospec=True)
    def test_claude_model_routes_to_chatanthropic(self, mock_cls):
        from importlib import reload

        import prismai.llm.client as mod

        reload(mod)
        mock_cls.return_value = MagicMock()
        result = mod.criar_llm(model="claude-3-5-sonnet-20241022")
        mock_cls.assert_called_once_with(
            model="claude-3-5-sonnet-20241022", temperature=0, timeout=60, max_retries=0,
        )
        assert result is mock_cls.return_value

    @patch("langchain_openai.ChatOpenAI", autospec=True)
    def test_default_model_is_openai(self, mock_cls):
        from importlib import reload

        import prismai.llm.client as mod

        reload(mod)
        mock_cls.return_value = MagicMock()
        mod.criar_llm()
        mock_cls.assert_called_once()
        assert mock_cls.call_args[1]["model"] == "gpt-4o-mini"
