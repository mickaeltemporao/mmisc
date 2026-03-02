def make_table(
    """Takes a list of statsmodels and returns a typst table."""
    models, 
    model_names=None, 
    dep_var="Name Your DV",
    imp=None, 
    note="`*` indicates p < 0.05",
    output_path='model_summary.typ',
    as_file=False,
):
    if not isinstance(models, list):
        models = [models]
    if model_names is None:
        model_names = [f"*Model {i+1}*" for i in range(len(models))]
    else:
        model_names = [f"*{i}*" for i in model_names]

    def star(p):
        return "`*`" if p < 0.05 else ""

    def fmt_coef(coef, pval):
        return f"{coef:.1f}{star(pval)}"

    def fmt_se(seval):
        return f"({seval:.1f})"

    # Collect all variable names across all models to align rows
    all_vars = set()
    for model in models:
        all_vars.update(model.params.index)
    all_vars = list(all_vars)
    all_vars.sort()
    all_vars.remove("Intercept")
    all_vars.append("Intercept")
    # TODO: Add logic to match specified vars.
    if imp:
        if not isinstance(imp, list):
            imp = [imp]
        for i in imp:
            try:
                all_vars.remove(i)
                all_vars.insert(0, i)
            except Exception as e:
                raise "Imp list NOT in column names"

    lines = []
    for var in all_vars:
        row = f"  [_`{var}`_]"
        for model in models:
            if var in model.params.index:
                coef = fmt_coef(model.params[var], model.pvalues[var])
                se = fmt_se(model.bse[var])
                row += f", [{coef} {se}]"
            else:
                row += ", [ ]"
        row += ","
        lines.append(row)

    lines.append("  table.hline(),")
    lines = [s.replace("T.", "") for s in lines]

    # Observations row
    row = "  [Observations]"
    for model in models:
        row += f", [{int(model.nobs)}]"
    row += ","
    lines.append(row)

    # R² row
    row = "  [R²]"
    for model in models:
        row += f", [{model.rsquared:.2f}]"
    row += ","
    lines.append(row)

    # Header construction

    header = f"""#table(
    columns: {len(models) + 1},
    align: (left, {'center,'*len(models)}),
    [], table.cell(colspan: {len(models)}, [_{dep_var}_]),
    table.hline(),
    stroke: (x: none, y: none),
      [], [{'], ['.join(model_names)}],
      [], {'[β (_SE_)],'*len(models)}
    table.hline(),
"""

    footer = f"""  table.hline(),
align(left, [_Note._ {note}])
)"""
    output = header + "\n".join(lines) + "\n" + footer
    if as_file:
        with open(output_path, "w") as text_file:
            text_file.write(output)
    else:
        print(output)
