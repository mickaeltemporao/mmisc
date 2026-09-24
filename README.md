# Mickael's Miscellaneous Python Helpers and Utility Functions.

## Usage

### Typst Regression Tables

Generate publication-ready [Typst](https://typst.app/) regression tables directly from `statsmodels` results:

```python
import statsmodels.formula.api as smf
from mmisc import make_table

model1 = smf.ols("y ~ x1", data=df).fit()
model2 = smf.ols("y ~ x1 + x2", data=df).fit()

# Return Typst markup string
typst_code = make_table(
    [model1, model2],
    model_names=["Baseline", "Full"],
    dep_var="Outcome",
    var_labels={"x1": "Feature 1", "x2": "Feature 2"},
    stats=("nobs", "r2", "aic"),
)

# Or write directly to file
make_table([model1, model2], output_path="models.typ")
```

## Publishing to PyPI

1. **Configure Token** (one-time setup in `.env`):
   ```bash
   export UV_PUBLISH_TOKEN=pypi-...
   ```

2. **Build and Publish**:
   ```bash
   rm -rf dist/
   dotenv run -- uv build
   dotenv run -- uv publish
   ```

3. **Tag and Push**:
   ```bash
   git tag v<version>
   git push origin main --tags
   ```
