"""Pure-Python statistical distribution functions (no scipy dependency)."""
from __future__ import annotations

import math

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)
_LN_SQRT2PI = 0.5 * math.log(2.0 * math.pi)


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT2PI


def norm_sf(x: float) -> float:
    """Standard normal survival function P(Z > x)."""
    return 0.5 * math.erfc(x / _SQRT2)


def norm_ppf(p: float) -> float:
    """Inverse normal CDF via rational approximation + Newton refinement."""
    if p <= 0:
        return float("-inf")
    if p >= 1:
        return float("inf")
    if p == 0.5:
        return 0.0

    sign = -1.0
    q = p
    if p > 0.5:
        q = 1.0 - p
        sign = 1.0

    t = math.sqrt(-2.0 * math.log(q))
    # Abramowitz & Stegun 26.2.23
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    x0 = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)

    # Newton refinement: x0 is for the upper tail
    for _ in range(3):
        phi = norm_sf(x0)  # P(Z > x0)
        pdf = _norm_pdf(x0)
        if pdf == 0:
            break
        x0 -= (phi - q) / (-pdf)  # derivative of norm_sf is -pdf

    return sign * x0


def _lgamma(x: float) -> float:
    return math.lgamma(x)


def _regularized_gamma_inc(a: float, x: float) -> float:
    """Lower regularized incomplete gamma P(a, x) via series expansion."""
    if x < 0:
        return 0.0
    if x == 0:
        return 0.0
    if x > a + 1:
        return 1.0 - _regularized_gamma_inc_upper(a, x)

    ap = a
    s = 1.0 / a
    ds = s
    for _ in range(300):
        ap += 1.0
        ds *= x / ap
        s += ds
        if abs(ds) < abs(s) * 1e-15:
            break
    return s * math.exp(-x + a * math.log(x) - _lgamma(a))


def _regularized_gamma_inc_upper(a: float, x: float) -> float:
    """Upper regularized incomplete gamma Q(a, x) via continued fraction."""
    b = x + 1.0 - a
    c = 1.0 / 1e-30
    d = 1.0 / b
    h = d
    for i in range(1, 300):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h * math.exp(-x + a * math.log(x) - _lgamma(a))


def chi2_sf(x: float, df: int) -> float:
    """Chi-squared survival function P(X > x) with df degrees of freedom."""
    if x <= 0:
        return 1.0
    if df <= 0:
        return 0.0
    return _regularized_gamma_inc_upper(df / 2.0, x / 2.0)


def _regularized_beta_inc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b) via continued fraction (Lentz)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _regularized_beta_inc(b, a, 1.0 - x)

    lbeta = _lgamma(a) + _lgamma(b) - _lgamma(a + b)
    log_front = a * math.log(x) + b * math.log(1.0 - x) - lbeta - math.log(a)

    # Lentz's continued fraction for I_x(a, b)
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        # even step
        num = m * (b - m) * x / ((a + 2.0 * m - 1.0) * (a + 2.0 * m))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c

        # odd step
        num = -(a + m) * (a + b + m) * x / ((a + 2.0 * m) * (a + 2.0 * m + 1.0))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break

    return math.exp(log_front) * h * a


def t_sf(x: float, df: int) -> float:
    """Student's t survival function P(T > x) with df degrees of freedom (one-tailed)."""
    if df <= 0:
        return 0.0
    # For large df, use normal approximation
    if df > 100:
        return norm_sf(x)
    t2 = x * x
    p = 0.5 * _regularized_beta_inc(df / 2.0, 0.5, df / (df + t2))
    if x >= 0:
        return p
    return 1.0 - p
