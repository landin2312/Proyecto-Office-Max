from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


BASE_FEATURES = [
    "ln_precio",
    "margen",
    "ln_costo_unitario",
    "fechas_venta",
    "mes_num",
    "anio",
]

CATEGORICAL_FEATURES = [
    "dept_nm",
    "subdept_nm",
    "tipo_marca",
    "store_nbr",
]


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")


def clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def load_base(path: Path, dept: str | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df["fecha"] = pd.to_datetime(df["tran_date"], dayfirst=True, errors="coerce")
    df["anio"] = df["fecha"].dt.year
    df["mes_num"] = df["fecha"].dt.month
    for col in ["prod_nbr", "store_nbr", "dept_nm", "subdept_nm", "tipo_marca", "marca"]:
        df[col] = clean_text(df[col])
    for col in ["qty", "precio", "margen", "costo calculado", "apparent_unit cost"]:
        df[col] = numeric(df[col])

    if dept:
        df = df[df["dept_nm"].str.upper() == dept.strip().upper()].copy()

    df["costo_unitario"] = df["costo calculado"].fillna(df["apparent_unit cost"])
    df = df[(df["qty"] > 0) & (df["precio"] > 0) & (df["costo_unitario"] > 0)].copy()
    df = build_model_table(df)
    if dept:
        df = df[df["dept_nm"].str.upper() == dept.strip().upper()].copy()
    return df


def build_model_table(raw: pd.DataFrame) -> pd.DataFrame:
    dims = ["prod_nbr", "store_nbr", "dept_nm", "subdept_nm", "tipo_marca", "marca", "anio", "mes_num"]
    df = (
        raw.groupby(dims, dropna=False, as_index=False)
        .agg(
            qty=("qty", "sum"),
            precio=("precio", "mean"),
            margen=("margen", "mean"),
            costo_unitario=("costo_unitario", "mean"),
            transacciones=("tran_nbr", "nunique"),
            fechas_venta=("fecha", "nunique"),
        )
    )
    df = df[(df["qty"] > 0) & (df["precio"] > 0) & (df["costo_unitario"] > 0)].copy()
    df["ln_qty"] = np.log(df["qty"])
    df["ln_precio"] = np.log(df["precio"])
    df["ln_costo_unitario"] = np.log(df["costo_unitario"])
    df["ln_transacciones"] = np.log(df["transacciones"].clip(lower=1))
    df["margen"] = df["margen"].fillna(df["margen"].median())
    return df.dropna(subset=["ln_qty", "ln_precio", "ln_costo_unitario", "ln_transacciones", "margen", "anio", "mes_num"])


def make_design(df: pd.DataFrame, include_categoricals: bool = True) -> tuple[pd.DataFrame, pd.Series]:
    cols = BASE_FEATURES.copy()
    data = df[cols].copy()
    if include_categoricals:
        dummies = pd.get_dummies(df[CATEGORICAL_FEATURES], drop_first=True, dtype=float)
        data = pd.concat([data, dummies], axis=1)
    return data.astype(float), df["ln_qty"].astype(float)


def fit_model(df: pd.DataFrame, include_categoricals: bool = True) -> tuple[LinearRegression, pd.DataFrame, float, int]:
    x, y = make_design(df, include_categoricals=include_categoricals)
    model = LinearRegression()
    model.fit(x, y)
    pred = model.predict(x)
    r2 = r2_score(y, pred)
    coef = pd.DataFrame({"variable": x.columns, "coeficiente": model.coef_})
    coef["abs_coeficiente"] = coef["coeficiente"].abs()
    coef = coef.sort_values("abs_coeficiente", ascending=False).reset_index(drop=True)
    return model, coef, float(r2), len(df)


def global_summary(df: pd.DataFrame, dept: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    _model, coef, r2, n = fit_model(df, include_categoricals=True)
    beta_precio = float(coef.loc[coef["variable"] == "ln_precio", "coeficiente"].iloc[0])
    summary = pd.DataFrame(
        [
            {"metric": "departamento", "valor": dept or "TODOS"},
            {"metric": "n_observaciones", "valor": n},
            {"metric": "skus", "valor": df["prod_nbr"].nunique()},
            {"metric": "tiendas", "valor": df["store_nbr"].nunique()},
            {"metric": "r2_modelo", "valor": r2},
            {"metric": "elasticidad_precio_ln_precio", "valor": beta_precio},
        ]
    )
    return summary, coef


def sku_models(df: pd.DataFrame, min_obs: int = 12) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for sku, group in df.groupby("prod_nbr"):
        if len(group) < min_obs:
            rows.append({"SKU": sku, "n_observaciones": len(group), "r2": np.nan, "beta_precio": np.nan, "estatus": "n insuficiente"})
            continue
        if group["precio"].nunique() < 2:
            rows.append({"SKU": sku, "n_observaciones": len(group), "r2": np.nan, "beta_precio": np.nan, "estatus": "precio constante"})
            continue
        if group["qty"].nunique() < 2:
            rows.append({"SKU": sku, "n_observaciones": len(group), "r2": np.nan, "beta_precio": np.nan, "estatus": "qty constante"})
            continue
        try:
            _model, coef, r2, n = fit_model(group, include_categoricals=False)
            beta = float(coef.loc[coef["variable"] == "ln_precio", "coeficiente"].iloc[0])
            rows.append({"SKU": sku, "n_observaciones": n, "r2": r2, "beta_precio": beta, "estatus": "valida"})
        except Exception as exc:
            rows.append({"SKU": sku, "n_observaciones": len(group), "r2": np.nan, "beta_precio": np.nan, "estatus": type(exc).__name__})
    return pd.DataFrame(rows)


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dept, group in df.groupby("dept_nm"):
        try:
            _model, coef, r2, n = fit_model(group, include_categoricals=True)
            beta = float(coef.loc[coef["variable"] == "ln_precio", "coeficiente"].iloc[0])
            rows.append(
                {
                    "dept_nm": dept,
                    "n_observaciones": n,
                    "skus": group["prod_nbr"].nunique(),
                    "tiendas": group["store_nbr"].nunique(),
                    "r2_modelo": r2,
                    "beta_precio": beta,
                }
            )
        except Exception as exc:
            rows.append({"dept_nm": dept, "n_observaciones": len(group), "skus": group["prod_nbr"].nunique(), "tiendas": group["store_nbr"].nunique(), "r2_modelo": np.nan, "beta_precio": np.nan, "error": str(exc)})
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Modelo log-log multivariable para Base_OfficeMax19mayo.")
    parser.add_argument("--input", default=Path("Base_OfficeMax19mayo.csv"), type=Path)
    parser.add_argument("--output-dir", default=Path("output/base19mayo"), type=Path)
    parser.add_argument("--dept", default=None, help="Opcional: filtrar dept_nm exacto.")
    parser.add_argument("--min-obs-sku", default=12, type=int)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    df_all = load_base(args.input, dept=None)
    df = df_all if not args.dept else df_all[df_all["dept_nm"].str.upper() == args.dept.strip().upper()].copy()
    suffix = "" if not args.dept else "_" + args.dept.strip().upper().replace(" ", "_")

    summary, coef = global_summary(df, args.dept)
    sku = sku_models(df, min_obs=args.min_obs_sku)
    dept_summary = category_summary(df_all)

    summary_path = args.output_dir / f"modelo2_multivariable_resumen{suffix}.csv"
    coef_path = args.output_dir / f"modelo2_multivariable_coeficientes{suffix}.csv"
    sku_path = args.output_dir / f"modelo2_multivariable_sku{suffix}.csv"
    dept_path = args.output_dir / "modelo2_multivariable_por_departamento.csv"

    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    coef.to_csv(coef_path, index=False, encoding="utf-8-sig")
    sku.to_csv(sku_path, index=False, encoding="utf-8-sig")
    dept_summary.to_csv(dept_path, index=False, encoding="utf-8-sig")

    valid_sku = int((sku["estatus"] == "valida").sum())
    print("Modelo 2 multivariable")
    print(f"departamento: {args.dept or 'TODOS'}")
    print(f"observaciones: {len(df)}")
    print(f"SKUs: {df['prod_nbr'].nunique()}")
    print(f"SKUs con modelo valido: {valid_sku}")
    print(f"R2 global: {summary.loc[summary['metric'] == 'r2_modelo', 'valor'].iloc[0]}")
    print(f"Beta precio global: {summary.loc[summary['metric'] == 'elasticidad_precio_ln_precio', 'valor'].iloc[0]}")
    print(f"salida resumen: {summary_path}")
    print(f"salida coeficientes: {coef_path}")
    print(f"salida SKU: {sku_path}")
    print(f"salida por departamento: {dept_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
