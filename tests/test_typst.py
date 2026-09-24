from __future__ import annotations

import pandas as pd
import pytest
from mmisc import make_table
from mmisc.typst import make_table as make_table_direct


class MockRegressionResults:
    def __init__(
        self,
        params: dict[str, float],
        pvalues: dict[str, float],
        bse: dict[str, float],
        nobs: int = 100,
        rsquared: float | None = 0.45,
        rsquared_adj: float | None = 0.42,
        aic: float | None = 150.0,
        bic: float | None = 160.0,
        fvalue: float | None = 25.5,
        prsquared: float | None = None,
    ):
        self.params = pd.Series(params)
        self.pvalues = pd.Series(pvalues)
        self.bse = pd.Series(bse)
        self.nobs = nobs
        self.rsquared = rsquared
        self.rsquared_adj = rsquared_adj
        self.aic = aic
        self.bic = bic
        self.fvalue = fvalue
        self.prsquared = prsquared


@pytest.fixture
def model1():
    return MockRegressionResults(
        params={"Intercept": 2.50, "x1": 1.234, "x2": -0.567},
        pvalues={"Intercept": 0.001, "x1": 0.02, "x2": 0.15},
        bse={"Intercept": 0.25, "x1": 0.12, "x2": 0.30},
        nobs=120,
        rsquared=0.65,
    )


@pytest.fixture
def model2():
    return MockRegressionResults(
        params={"Intercept": 1.80, "x1": 0.987, "x3": 3.456},
        pvalues={"Intercept": 0.0001, "x1": 0.04, "x3": 0.002},
        bse={"Intercept": 0.20, "x1": 0.10, "x3": 0.50},
        nobs=120,
        rsquared=0.72,
    )


def test_imports():
    assert make_table is make_table_direct


def test_single_model_defaults(model1):
    output = make_table(model1)
    assert isinstance(output, str)
    assert "#figure(" in output
    assert "caption: [Regression results for Name Your DV]" in output
    assert "columns: 2" in output
    assert "align: (left, center)" in output
    assert "[*Model 1*]" in output
    assert "[1.23`*` (0.12)]" in output
    assert "[Observations], [120]" in output
    assert "[R²], [0.65]" in output
    assert "_Note._ `*` indicates p < 0.05" in output


def test_multiple_models_custom_names_and_caption(model1, model2):
    output = make_table(
        [model1, model2],
        model_names=["Baseline", "Full"],
        dep_var="Log Wage",
        caption="Estimated Wage Models",
    )
    assert "caption: [Estimated Wage Models]" in output
    assert "[_Log Wage_]" in output
    assert "[*Baseline*]" in output
    assert "[*Full*]" in output
    assert "columns: 3" in output
    assert "align: (left, center, center)" in output
    # x2 should be empty in model2, x3 empty in model1
    assert "[-0.57 (0.30)], [ ]" in output
    assert "[ ], [3.46`*` (0.50)]" in output


def test_imp_ordering(model1, model2):
    # Alphabetical order without imp would be x1, x2, x3, Intercept
    output = make_table([model1, model2], imp=["x2", "x1"])
    lines = output.splitlines()
    var_lines = [line.strip() for line in lines if "[_`" in line]
    assert "[_`x2`_]" in var_lines[0]
    assert "[_`x1`_]" in var_lines[1]
    assert "[_`x3`_]" in var_lines[2]
    assert "[_`Intercept`_]" in var_lines[3]


def test_imp_invalid_var_raises(model1):
    with pytest.raises(ValueError, match="Variable 'non_existent' in imp is not present"):
        make_table(model1, imp=["non_existent"])


def test_model_without_intercept():
    model_no_int = MockRegressionResults(
        params={"x1": 1.5, "x2": 2.0},
        pvalues={"x1": 0.01, "x2": 0.03},
        bse={"x1": 0.3, "x2": 0.4},
    )
    output = make_table(model_no_int)
    assert "[_`Intercept`_]" not in output
    assert "[_`x1`_]" in output
    assert "[_`x2`_]" in output


def test_var_labels_and_patsy_cleaning():
    model = MockRegressionResults(
        params={"T.treatment": 1.2, "age": 0.5, "Intercept": 3.0},
        pvalues={"T.treatment": 0.02, "age": 0.1, "Intercept": 0.001},
        bse={"T.treatment": 0.2, "age": 0.1, "Intercept": 0.3},
    )
    output = make_table(model, var_labels={"age": "Age in Years"})
    # Custom label
    assert "[_Age in Years_]" in output
    # Patsy T. stripped
    assert "[_`treatment`_]" in output


def test_digits_and_stars(model1):
    output = make_table(
        model1,
        digits=3,
        stars={0.001: "***", 0.01: "**", 0.05: "*"},
    )
    # Check 3 decimal places
    assert "[1.234`*` (0.120)]" in output
    # Intercept pval is 0.001, not strictly < 0.001, so < 0.01 applies -> **
    assert "[2.500`**` (0.250)]" in output
    assert "`*` indicates p < 0.05, `**` indicates p < 0.01, `***` indicates p < 0.001" in output


def test_summary_stats_and_fallback(model1):
    # Logit model with prsquared instead of rsquared
    logit_model = MockRegressionResults(
        params={"x1": 0.8, "Intercept": -1.2},
        pvalues={"x1": 0.03, "Intercept": 0.01},
        bse={"x1": 0.2, "Intercept": 0.3},
        rsquared=None,
        rsquared_adj=None,
        prsquared=0.28,
        aic=210.45,
        bic=225.12,
        fvalue=14.8,
    )
    output = make_table(
        logit_model,
        stats=("nobs", "r2", "adj_r2", "aic", "bic", "f_stat"),
    )
    assert "[Observations], [100]" in output
    # Falls back to prsquared
    assert "[R²], [0.28]" in output
    assert "[Adj. R²], []" in output
    assert "[AIC], [210.45]" in output
    assert "[BIC], [225.12]" in output
    assert "[F-statistic], [14.80]" in output


def test_output_to_file(tmp_path, model1):
    target = tmp_path / "out.typ"
    output = make_table(model1, output_path=str(target))
    assert target.exists()
    assert target.read_text(encoding="utf-8") == output


def test_real_statsmodels_ols():
    import numpy as np
    import statsmodels.api as sm

    np.random.seed(42)
    x = np.random.randn(100, 2)
    y = 1.5 + 2.0 * x[:, 0] - 0.5 * x[:, 1] + np.random.randn(100) * 0.1
    x_with_const = sm.add_constant(x)
    model = sm.OLS(y, x_with_const).fit()

    output = make_table(
        model,
        var_labels={"const": "Constant", "x1": "Feature 1", "x2": "Feature 2"},
        dep_var="Response",
    )
    assert "#figure(" in output
    assert "caption: [Regression results for Response]" in output
    assert "[_Constant_]" in output
    assert "[_Feature 1_]" in output
    assert "[_Feature 2_]" in output
    assert "[Observations], [100]" in output
    assert "[R²]" in output

