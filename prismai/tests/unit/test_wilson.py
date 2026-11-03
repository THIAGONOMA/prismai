from prismai.eval.stats import wilson


class TestWilson:
    def test_high_success_rate(self):
        lo, hi = wilson(11, 11)
        assert lo > 0.7
        assert hi <= 1.0

    def test_zero_successes(self):
        lo, hi = wilson(0, 10)
        assert lo == 0.0
        assert hi > 0.0

    def test_half_successes(self):
        lo, hi = wilson(5, 10)
        assert lo < 0.5
        assert hi > 0.5
        assert abs((lo + hi) / 2 - 0.5) < 0.1

    def test_empty_sample(self):
        assert wilson(0, 0) == (0.0, 1.0)
