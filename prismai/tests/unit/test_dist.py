"""Tests for prismai.synthesis.dist — statistical distribution functions."""
from __future__ import annotations

from prismai.synthesis.dist import chi2_sf, norm_ppf, norm_sf, t_sf


class TestNormSf:
    def test_z_0(self):
        assert abs(norm_sf(0) - 0.5) < 1e-4

    def test_z_196(self):
        assert abs(norm_sf(1.96) - 0.025) < 1e-3

    def test_z_negative(self):
        assert abs(norm_sf(-1.96) - 0.975) < 1e-3


class TestChi2Sf:
    def test_chi2_384_df1(self):
        assert abs(chi2_sf(3.841, 1) - 0.05) < 1e-2

    def test_chi2_0(self):
        assert chi2_sf(0, 5) == 1.0


class TestTSf:
    def test_t_large_df(self):
        p = t_sf(1.96, 1000)
        assert abs(p - 0.025) < 1e-2

    def test_t_small_df(self):
        p = t_sf(2.776, 4)
        assert p < 0.06


class TestNormPpf:
    def test_ppf_05(self):
        assert abs(norm_ppf(0.5)) < 1e-6

    def test_ppf_025(self):
        assert abs(norm_ppf(0.025) - (-1.96)) < 0.01

    def test_ppf_975(self):
        assert abs(norm_ppf(0.975) - 1.96) < 0.01
