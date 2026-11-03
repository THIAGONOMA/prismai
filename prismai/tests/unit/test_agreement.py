from prismai.eval.agreement import cohens_kappa, disagreement_score


class TestDisagreementScore:
    def test_same_decision_is_zero(self):
        assert disagreement_score("include", "include") == 0.0
        assert disagreement_score("exclude", "exclude") == 0.0

    def test_include_vs_exclude_is_highest(self):
        assert disagreement_score("include", "exclude") == 3.0
        assert disagreement_score("exclude", "include") == 3.0

    def test_include_vs_uncertain(self):
        assert disagreement_score("include", "uncertain") == 2.0
        assert disagreement_score("uncertain", "include") == 2.0

    def test_exclude_vs_uncertain(self):
        assert disagreement_score("exclude", "uncertain") == 1.0
        assert disagreement_score("uncertain", "exclude") == 1.0


class TestCohensKappa:
    def test_perfect_agreement(self):
        a = ["include", "exclude", "include"]
        b = ["include", "exclude", "include"]
        assert cohens_kappa(a, b) == 1.0

    def test_no_agreement(self):
        a = ["include", "exclude", "include", "exclude"]
        b = ["exclude", "include", "exclude", "include"]
        k = cohens_kappa(a, b)
        assert k < 0

    def test_partial_agreement(self):
        a = ["include", "exclude", "include", "exclude"]
        b = ["include", "exclude", "exclude", "exclude"]
        k = cohens_kappa(a, b)
        assert 0 < k < 1

    def test_empty_lists(self):
        assert cohens_kappa([], []) == 0.0

    def test_single_category_returns_zero(self):
        a = ["include", "include", "include"]
        b = ["include", "include", "include"]
        k = cohens_kappa(a, b)
        assert k == 0.0

    def test_mismatched_lengths_raises(self):
        import pytest

        with pytest.raises(ValueError):
            cohens_kappa(["a"], ["a", "b"])
