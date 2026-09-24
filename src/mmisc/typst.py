from __future__ import annotations

from typing import Any, Sequence


def _get_series(model: Any, attr: str):
    val = getattr(model, attr)
    if hasattr(val, "index"):
        return val
    exog_names = getattr(getattr(model, "model", None), "exog_names", None)
    if exog_names is not None:
        import pandas as pd
        return pd.Series(val, index=exog_names)
    import pandas as pd
    return pd.Series(val)


def _extract_r2(model: Any, digits: int) -> str:
    val = getattr(model, "rsquared", None)
    if val is None:
        val = getattr(model, "prsquared", None)
    if val is not None:
        return f"{val:.{digits}f}"
    return ""


STAT_HANDLERS = {
    "nobs": (
        "Observations",
        lambda m, d: f"{int(m.nobs)}" if hasattr(m, "nobs") and m.nobs is not None else "",
    ),
    "r2": ("R²", _extract_r2),
    "adj_r2": (
        "Adj. R²",
        lambda m, d: (
            f"{m.rsquared_adj:.{d}f}"
            if getattr(m, "rsquared_adj", None) is not None
            else ""
        ),
    ),
    "aic": (
        "AIC",
        lambda m, d: f"{m.aic:.{d}f}" if getattr(m, "aic", None) is not None else "",
    ),
    "bic": (
        "BIC",
        lambda m, d: f"{m.bic:.{d}f}" if getattr(m, "bic", None) is not None else "",
    ),
    "f_stat": (
        "F-statistic",
        lambda m, d: (
            f"{m.fvalue:.{d}f}" if getattr(m, "fvalue", None) is not None else ""
        ),
    ),
}


def make_table(
    models: Any,
    model_names: Sequence[str] | None = None,
    dep_var: str = "Name Your DV",
    caption: str | None = None,
    imp: Sequence[str] | str | None = None,
    var_labels: dict[str, str] | None = None,
    stats: Sequence[str] | tuple[str, ...] = ("nobs", "r2"),
    digits: int = 2,
    stars: dict[float, str] | None = None,
    note: str | None = None,
    output_path: str | None = None,
    as_file: bool = False,
) -> str:
    """Takes one or more statsmodels results and returns a Typst table formatted markup string.

    Parameters
    ----------
    models : statsmodels result object or sequence of result objects
        The fitted regression model(s).
    model_names : sequence of str, optional
        Header names for the models. Defaults to Model 1, Model 2, etc.
    dep_var : str, default "Name Your DV"
        Dependent variable name shown in the table header.
    caption : str, optional
        Caption for the Typst figure wrapper. Defaults to
        "Regression results for {dep_var}".
    imp : str or sequence of str, optional
        Variable name(s) to prioritize at the top of the table.
    var_labels : dict of str to str, optional
        Mapping from variable names to human-readable display labels.
    stats : sequence of str, default ("nobs", "r2")
        Summary statistics to report below the coefficients. Supported:
        "nobs", "r2", "adj_r2", "aic", "bic", "f_stat".
    digits : int, default 2
        Decimal places for coefficients, standard errors, and statistics.
    stars : dict of float to str, optional
        Significance thresholds mapped to star symbols.
        Defaults to `{0.05: "*"}`.
    note : str, optional
        Footnote below the table. Defaults to automatic note matching `stars`.
    output_path : str, optional
        File path to save the generated Typst markup. If provided or if `as_file`
        is True, the table is written to file.
    as_file : bool, default False
        Whether to write the output to `output_path` (default "model_summary.typ").

    Returns
    -------
    str
        The generated Typst markup.
    """
    if not isinstance(models, (list, tuple)):
        model_list = [models]
    else:
        model_list = list(models)

    if model_names is None:
        formatted_names = [f"*Model {i + 1}*" for i in range(len(model_list))]
    else:
        formatted_names = [f"*{name}*" for name in model_names]

    if stars is None:
        active_stars = {0.05: "*"}
    else:
        active_stars = dict(stars)

    # Sort thresholds in ascending order so the strictest (smallest p) matches first
    sorted_stars = sorted(active_stars.items(), key=lambda item: item[0])

    def star(p: float) -> str:
        for threshold, symbol in sorted_stars:
            if p < threshold:
                return f"`{symbol}`"
        return ""

    def fmt_coef(coef: float, pval: float) -> str:
        return f"{coef:.{digits}f}{star(pval)}"

    def fmt_se(seval: float) -> str:
        return f"({seval:.{digits}f})"

    # Normalize model series (handles both pandas Series and numpy ndarray results)
    model_data = [
        (
            _get_series(m, "params"),
            _get_series(m, "pvalues"),
            _get_series(m, "bse"),
            m,
        )
        for m in model_list
    ]

    # Collect all unique variable names across models
    all_vars_set = set()
    for params, _, _, _ in model_data:
        all_vars_set.update(params.index)
    all_vars = sorted(list(all_vars_set))

    # Move Intercept or const to the bottom if present
    for intercept_name in ("Intercept", "const"):
        if intercept_name in all_vars:
            all_vars.remove(intercept_name)
            all_vars.append(intercept_name)

    # Handle important / prioritized variables
    if imp is not None:
        if isinstance(imp, str):
            imp_list = [imp]
        else:
            imp_list = list(imp)

        for var in reversed(imp_list):
            if var not in all_vars:
                raise ValueError(
                    f"Variable '{var}' in imp is not present in model parameters"
                )
            all_vars.remove(var)
            all_vars.insert(0, var)

    lines: list[str] = []
    labels_map = var_labels if var_labels is not None else {}

    for var in all_vars:
        if var in labels_map:
            label = labels_map[var]
            row = f"  [_{label}_]"
        else:
            cleaned = var.replace("T.", "")
            row = f"  [_`{cleaned}`_]"

        for params, pvals, bse, _ in model_data:
            if var in params.index:
                coef = fmt_coef(params[var], pvals[var])
                se = fmt_se(bse[var])
                row += f", [{coef} {se}]"
            else:
                row += ", [ ]"
        row += ","
        lines.append(row)

    lines.append("    table.hline(),")

    # Add summary statistics rows
    if stats:
        for stat_key in stats:
            if stat_key in STAT_HANDLERS:
                label, extractor = STAT_HANDLERS[stat_key]
                row = f"    [{label}]"
                for model in model_list:
                    val = extractor(model, digits)
                    row += f", [{val}]"
                row += ","
                lines.append(row)
        lines.append("    table.hline(),")

    # Header and figure construction
    num_models = len(model_list)
    align_items = ["left"] + ["center"] * num_models
    align_str = "(" + ", ".join(align_items) + ")"

    fig_caption = (
        caption if caption is not None else f"Regression results for {dep_var}"
    )

    model_headers = ", ".join(f"[{m}]" for m in formatted_names)
    se_headers = ", ".join(["[β (_SE_)]"] * num_models)

    table_header = f"""#figure(
  caption: [{fig_caption}],
  table(
    columns: {num_models + 1},
    align: {align_str},
    stroke: none,
    table.hline(),
    [], table.cell(colspan: {num_models}, [_{dep_var}_]),
    table.hline(),
    [], {model_headers},
    [], {se_headers},
    table.hline(),
"""

    table_body = "\n".join(lines)
    table_footer = """  )
)"""

    if note is None:
        if active_stars:
            note_content = ", ".join(
                f"`{sym}` indicates p < {th}"
                for th, sym in sorted(
                    active_stars.items(), key=lambda x: x[0], reverse=True
                )
            )
        else:
            note_content = ""
    else:
        note_content = note

    if note_content:
        footer = f"{table_footer}\n#align(left)[_Note._ {note_content}]\n"
    else:
        footer = f"{table_footer}\n"

    output = table_header + table_body + "\n" + footer

    if as_file or output_path is not None:
        dest = output_path if output_path is not None else "model_summary.typ"
        with open(dest, "w", encoding="utf-8") as text_file:
            text_file.write(output)

    return output
