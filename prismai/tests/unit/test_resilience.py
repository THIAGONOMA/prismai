import json

import pytest

from prismai.agents.resilience import com_retry, parse_json_resposta


class TestComRetry:
    def test_succeeds_first_try(self):
        sleeps = []
        result = com_retry(lambda: 42, sleep_fn=sleeps.append)
        assert result == 42
        assert sleeps == []

    def test_retries_on_transient_error(self):
        sleeps = []
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("transient")
            return "ok"

        result = com_retry(
            flaky,
            max_tentativas=3,
            base=1.0,
            transient_errors=(ConnectionError,),
            sleep_fn=sleeps.append,
        )
        assert result == "ok"
        assert call_count == 2
        assert sleeps == [1.0]

    def test_no_retry_on_non_transient_error(self):
        sleeps = []

        def bad():
            raise ValueError("non-transient")

        with pytest.raises(ValueError, match="non-transient"):
            com_retry(bad, transient_errors=(ConnectionError,), sleep_fn=sleeps.append)
        assert sleeps == []

    def test_exhausts_retries(self):
        sleeps = []

        def always_fail():
            raise ConnectionError("fail")

        with pytest.raises(ConnectionError):
            com_retry(
                always_fail,
                max_tentativas=2,
                base=1.0,
                transient_errors=(ConnectionError,),
                sleep_fn=sleeps.append,
            )
        assert len(sleeps) == 2
        assert sleeps[0] == 1.0
        assert sleeps[1] == 2.0


class TestParseJsonResposta:
    def test_clean_json(self):
        r = parse_json_resposta('{"key": "value"}')
        assert r == {"key": "value"}

    def test_strips_markdown_fences(self):
        raw = '```json\n{"key": "value"}\n```'
        r = parse_json_resposta(raw)
        assert r == {"key": "value"}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_resposta("not json at all")
