from prismai.eval.stopping import should_stop


class TestShouldStop:
    def test_below_min_sample_never_stops(self):
        result = should_stop(10, 10, threshold=0.5)
        assert result["should_stop"] is False
        assert "min_sample" in result["reason"]

    def test_above_threshold_stops(self):
        result = should_stop(100, 99, threshold=0.90)
        assert result["should_stop"] is True
        assert result["lower_bound"] > 0.90

    def test_below_threshold_does_not_stop(self):
        result = should_stop(100, 60, threshold=0.90)
        assert result["should_stop"] is False

    def test_perfect_agreement_stops(self):
        result = should_stop(200, 200, threshold=0.95)
        assert result["should_stop"] is True
        assert result["agreement_rate"] == 1.0

    def test_zero_screened(self):
        result = should_stop(0, 0)
        assert result["should_stop"] is False
