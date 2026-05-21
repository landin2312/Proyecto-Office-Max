from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


WINDOWS = {"mensual": 1, "trimestral": 3, "semestral": 6}
REVIEW_FILES = ["Base_OfficeMax19mayo.csv"]


@dataclass(frozen=True)
class RegressionResult:
    beta: float | None
    alpha: float | None
    r2: float | None
    n: int
    status: str
    variables: list[str]


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")


def clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def classify(beta: float | None) -> str:
    if beta is None or pd.isna(beta):
        return "no_calculable"
    if beta < -1:
        return "elastico"
    if beta < 0:
        return "inelastico"
    return "beta_positiva_revision"


def review_columns() -> pd.DataFrame:
    rows = []
    for file in REVIEW_FILES:
        try:
            df = pd.read_csv(file, nrows=1, dtype=str, encoding="utf-8-sig")
            rows.append({"archivo": file, "existe": "SI", "columnas": ", ".join(df.columns), "detalle": ""})
        except Exception as exc:
            rows.append({"archivo": file, "existe": "NO", "columnas": "", "detalle": str(exc)})
    return pd.DataFrame(rows)


def load_base19(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    raw["fecha"] = pd.to_datetime(raw["tran_date"], dayfirst=True, errors="coerce")
    raw["period"] = raw["fecha"].dt.to_period("M")
    raw["mes"] = raw["period"].astype(str)
    for col in ["prod_nbr", "store_nbr", "dept_nm", "subdept_nm", "class_nm", "tipo_marca", "marca"]:
        if col in raw.columns:
            raw[col] = clean_text(raw[col])
    for col in ["qty", "precio", "net_sale", "margen", "costo calculado", "apparent_unit cost"]:
        if col in raw.columns:
            raw[col] = numeric(raw[col])
    raw["costo_unitario"] = raw["costo calculado"].fillna(raw["apparent_unit cost"])
    raw = raw[(raw["qty"] > 0) & (raw["precio"] > 0)].copy()

    dims = ["prod_nbr", "store_nbr", "period", "mes", "dept_nm", "subdept_nm", "class_nm", "tipo_marca", "marca"]
    master = (
        raw.groupby(dims, dropna=False, as_index=False)
        .agg(
            unidades=("qty", "sum"),
            net_sale=("net_sale", "sum"),
            precio_promedio=("precio", "mean"),
            margen=("margen", "mean"),
            costo_unitario=("costo_unitario", "mean"),
            transacciones=("tran_nbr", "nunique"),
            fechas_venta=("fecha", "nunique"),
        )
    )
    master["prod_nm"] = master["prod_nbr"]
    master["precio_real"] = master["net_sale"] / master["unidades"].replace(0, np.nan)
    master["precio_real"] = master["precio_real"].fillna(master["precio_promedio"])
    master = master[(master["unidades"] >= 0) & (master["precio_real"] > 0)].copy()
    master["period_start"] = master["period"].dt.to_timestamp()
    return master.sort_values(["prod_nbr", "period_start", "store_nbr"]).reset_index(drop=True)


def month_windows(group: pd.DataFrame, months: int) -> list[tuple[pd.Period, pd.Period]]:
    start = group["period"].min()
    end = group["period"].max()
    if pd.isna(start) or pd.isna(end):
        return []
    periods = pd.period_range(start, end, freq="M")
    windows = []
    for period in periods:
        period_end = period + (months - 1)
        if period_end <= end:
            windows.append((period, period_end))
    return windows


def simple_regression(window: pd.DataFrame) -> RegressionResult:
    clean = window[["unidades", "precio_real"]].dropna()
    clean = clean[(clean["unidades"] >= 0) & (clean["precio_real"] > 0)]
    n = len(clean)
    if n < 3:
        return RegressionResult(None, None, None, n, "n<3", ["log(precio_real)"])
    if clean["precio_real"].nunique() < 2:
        return RegressionResult(None, None, None, n, "precio constante", ["log(precio_real)"])
    if clean["unidades"].nunique() < 2:
        return RegressionResult(None, None, None, n, "unidades constantes", ["log(precio_real)"])
    x = np.log(clean["precio_real"].to_numpy(dtype=float)).reshape(-1, 1)
    y = np.log1p(clean["unidades"].to_numpy(dtype=float))
    model = LinearRegression().fit(x, y)
    pred = model.predict(x)
    return RegressionResult(float(model.coef_[0]), float(model.intercept_), float(r2_score(y, pred)), n, "calculada", ["log(precio_real)"])


def model2_regression(window: pd.DataFrame) -> RegressionResult:
    clean = window.copy()
    clean = clean[(clean["unidades"] >= 0) & (clean["precio_real"] > 0)].dropna(subset=["unidades", "precio_real"])
    n = len(clean)
    variables = ["log(precio_real)"]
    if n < 3:
        return RegressionResult(None, None, None, n, "n<3", variables)
    if clean["precio_real"].nunique() < 2:
        return RegressionResult(None, None, None, n, "precio constante", variables)
    if clean["unidades"].nunique() < 2:
        return RegressionResult(None, None, None, n, "unidades constantes", variables)

    x = pd.DataFrame({"log_precio_real": np.log(clean["precio_real"].astype(float))})
    for col, label in [("margen", "margen"), ("costo_unitario", "log(costo_unitario)"), ("fechas_venta", "fechas_venta")]:
        if col in clean.columns and clean[col].notna().any() and clean[col].nunique(dropna=True) > 1:
            if col == "costo_unitario":
                vals = clean[col].astype(float)
                if (vals > 0).all():
                    x["log_costo_unitario"] = np.log(vals)
                    variables.append(label)
            else:
                x[col] = clean[col].astype(float)
                variables.append(label)

    x["mes_num"] = clean["period"].dt.month.astype(float)
    variables.append("mes")

    # Categorical controls are only kept if they vary inside the SKU-window and do not overfit the window.
    if n < 8:
        categorical_controls = []
    else:
        categorical_controls = [("store_nbr", "tienda"), ("tipo_marca", "tipo_marca"), ("marca", "marca"), ("dept_nm", "departamento"), ("subdept_nm", "subdepartamento"), ("class_nm", "clase")]
    for col, label in categorical_controls:
        if col in clean.columns and clean[col].nunique(dropna=True) > 1:
            dummies = pd.get_dummies(clean[col].fillna("NA"), prefix=col, drop_first=True, dtype=float)
            if len(x.columns) + len(dummies.columns) + 2 < n:
                x = pd.concat([x.reset_index(drop=True), dummies.reset_index(drop=True)], axis=1)
                variables.append(label)

    if len(x.columns) + 1 >= n:
        return RegressionResult(None, None, None, n, "controles>observaciones", variables)

    y = np.log1p(clean["unidades"].to_numpy(dtype=float))
    model = LinearRegression().fit(x, y)
    pred = model.predict(x)
    beta = float(model.coef_[list(x.columns).index("log_precio_real")])
    return RegressionResult(beta, float(model.intercept_), float(r2_score(y, pred)), n, "calculada", variables)


def build_model_outputs(master: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows1 = []
    rows2 = []
    diag = []
    for sku, group in master.groupby("prod_nbr", sort=False):
        prod_nm = group["prod_nm"].dropna().iloc[0] if group["prod_nm"].notna().any() else sku
        for window_name, months in WINDOWS.items():
            for start, end in month_windows(group, months):
                window = group[(group["period"] >= start) & (group["period"] <= end)]
                inicio = start.to_timestamp().date().isoformat()
                fin = end.to_timestamp(how="end").date().isoformat()

                result1 = simple_regression(window)
                rows1.append(
                    {
                        "sku": sku,
                        "prod_nm": prod_nm,
                        "tipo_ventana": window_name,
                        "periodo_inicio": inicio,
                        "periodo_fin": fin,
                        "beta_precio": result1.beta,
                        "alpha": result1.alpha,
                        "r2": result1.r2,
                        "n_observaciones": result1.n,
                        "clasificacion_elasticidad": classify(result1.beta),
                    }
                )
                diag.append({"modelo": "modelo1", "razon": result1.status, "sku": sku, "tipo_ventana": window_name})

                result2 = model2_regression(window)
                rows2.append(
                    {
                        "sku": sku,
                        "prod_nm": prod_nm,
                        "tipo_ventana": window_name,
                        "periodo_inicio": inicio,
                        "periodo_fin": fin,
                        "beta_precio": result2.beta,
                        "r2": result2.r2,
                        "n_observaciones": result2.n,
                        "variables_usadas": ", ".join(result2.variables),
                        "clasificacion_elasticidad": classify(result2.beta),
                    }
                )
                diag.append({"modelo": "modelo2", "razon": result2.status, "sku": sku, "tipo_ventana": window_name})
    return pd.DataFrame(rows1), pd.DataFrame(rows2), pd.DataFrame(diag)


def build_summary(model1: pd.DataFrame, model2: pd.DataFrame, diag: pd.DataFrame, columns_review: pd.DataFrame) -> dict[str, pd.DataFrame]:
    def summary_for(df: pd.DataFrame, model_name: str) -> pd.DataFrame:
        total = len(df)
        calc = int(df["beta_precio"].notna().sum())
        return pd.DataFrame(
            [
                {"metric": "modelo", "valor": model_name},
                {"metric": "skus_analizados", "valor": df["sku"].nunique()},
                {"metric": "ventanas_totales", "valor": total},
                {"metric": "betas_calculadas", "valor": calc},
                {"metric": "porcentaje_betas_calculadas", "valor": calc / total * 100 if total else 0},
                {"metric": "porcentaje_betas_positivas", "valor": (df["clasificacion_elasticidad"].eq("beta_positiva_revision").mean() * 100) if total else 0},
                {"metric": "porcentaje_elasticas", "valor": (df["clasificacion_elasticidad"].eq("elastico").mean() * 100) if total else 0},
                {"metric": "porcentaje_inelasticas", "valor": (df["clasificacion_elasticidad"].eq("inelastico").mean() * 100) if total else 0},
            ]
        )

    resumen_general = pd.concat([summary_for(model1, "modelo1"), summary_for(model2, "modelo2")], ignore_index=True)
    diag_counts = diag.groupby(["modelo", "razon"], as_index=False).size().rename(columns={"size": "ventanas"})
    diag_counts["porcentaje"] = diag_counts.groupby("modelo")["ventanas"].transform(lambda s: s / s.sum() * 100)
    omitted = pd.DataFrame(
        [
            {"variable": "promocion / indicador_promocion", "estatus": "omitida en Base_OfficeMax19mayo.csv; no existe columna equivalente"},
            {"variable": "descuento_pct", "estatus": "omitida en Base_OfficeMax19mayo.csv; no existe columna equivalente"},
            {"variable": "tipo_promo", "estatus": "omitida en Base_OfficeMax19mayo.csv; no existe columna equivalente"},
            {"variable": "prod_nm", "estatus": "omitida en Base_OfficeMax19mayo.csv; se usa sku como identificador en columna prod_nm"},
            {"variable": "tienda", "estatus": "usada como control si varia y hay suficientes observaciones"},
            {"variable": "mes", "estatus": "usada como control"},
            {"variable": "marca / tipo_marca / departamento / subdepartamento / clase", "estatus": "usadas si varian dentro de la ventana y hay suficientes observaciones"},
        ]
    )
    diagnostico = pd.concat(
        [
            diag_counts.assign(tipo="razones_calculo"),
            omitted.rename(columns={"variable": "modelo", "estatus": "razon"}).assign(ventanas="", porcentaje="", tipo="variables_modelo2"),
            columns_review.rename(columns={"archivo": "modelo", "columnas": "razon"}).assign(ventanas="", porcentaje="", tipo="columnas_revisadas"),
        ],
        ignore_index=True,
    )
    calculated1 = model1[model1["beta_precio"].notna()].copy()
    top_elastic = calculated1[calculated1["clasificacion_elasticidad"] == "elastico"].sort_values("beta_precio").head(50)
    top_inelastic = calculated1[calculated1["clasificacion_elasticidad"] == "inelastico"].sort_values("beta_precio", ascending=False).head(50)
    positive = calculated1[calculated1["clasificacion_elasticidad"] == "beta_positiva_revision"].sort_values("beta_precio", ascending=False).head(100)
    return {
        "resumen_general": resumen_general,
        "modelo1_betas": model1,
        "modelo2_betas": model2,
        "diagnostico": diagnostico,
        "top_skus_elasticos": top_elastic,
        "top_skus_inelasticos": top_inelastic,
        "betas_positivas_revision": positive,
    }


def save_graphs_from_model1(model1: pd.DataFrame, output_dir: Path) -> tuple[list[str], pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    valid = model1[model1["beta_precio"].notna()].copy()
    if valid.empty:
        return [], pd.DataFrame(columns=["sku", "prod_nm", "betas_validas"])
    selected = (
        valid.groupby(["sku", "prod_nm"], as_index=False)
        .size()
        .rename(columns={"size": "betas_validas"})
        .sort_values("betas_validas", ascending=False)
        .head(3)
    )
    saved = []
    for row in selected.itertuples(index=False):
        sku = str(row.sku)
        data = model1[model1["sku"] == sku].copy()
        if data.empty:
            continue
        data["periodo_inicio"] = pd.to_datetime(data["periodo_inicio"], errors="coerce")
        fig, ax = plt.subplots(figsize=(11, 6))
        for window_name, color in [("mensual", "#2563eb"), ("trimestral", "#059669"), ("semestral", "#dc2626")]:
            series = data[(data["tipo_ventana"] == window_name) & data["beta_precio"].notna()].sort_values("periodo_inicio")
            if series.empty:
                continue
            ax.plot(series["periodo_inicio"], series["beta_precio"], marker="o", linewidth=1.8, label=window_name, color=color)
        ax.axhline(-1, color="#111827", linestyle="--", linewidth=1, label="umbral elastico")
        ax.axhline(0, color="#6b7280", linewidth=1)
        ax.set_title(f"Elasticidad dinamica Base 19 mayo - SKU {sku}")
        ax.set_xlabel("Periodo inicio")
        ax.set_ylabel("Beta precio")
        ax.grid(alpha=0.25)
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()
        path = output_dir / f"elasticidad_sku_{sku}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        saved.append(str(path))
    return saved, selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Entrega final de analisis de elasticidad.")
    parser.add_argument("--base", default=Path("Base_OfficeMax19mayo.csv"), type=Path)
    parser.add_argument("--output-dir", default=Path("output"), type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    columns_review = review_columns()
    master = load_base19(args.base)
    model1, model2, diag = build_model_outputs(master)

    model1_path = args.output_dir / "modelo1_betas_loglog.csv"
    model2_path = args.output_dir / "modelo2_betas_con_controles.csv"
    xlsx_path = args.output_dir / "resumen_elasticidad_entrega.xlsx"
    graph_dir = args.output_dir / "graficas_elasticidad"

    model1.to_csv(model1_path, index=False, encoding="utf-8-sig")
    model2.to_csv(model2_path, index=False, encoding="utf-8-sig")
    sheets = build_summary(model1, model2, diag, columns_review)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)

    saved_graphs, selected_graph_skus = save_graphs_from_model1(model1, graph_dir)
    selected_graph_skus.to_csv(args.output_dir / "skus_graficados_base19mayo.csv", index=False, encoding="utf-8-sig")

    def print_stats(name: str, df: pd.DataFrame) -> None:
        total = len(df)
        calc = int(df["beta_precio"].notna().sum())
        print(f"{name}:")
        print(f"  SKUs analizados: {df['sku'].nunique()}")
        print(f"  betas calculadas: {calc} de {total}")
        print("  betas por tipo de ventana:")
        print(df.groupby("tipo_ventana")["beta_precio"].count().to_string())
        print(f"  % betas positivas: {df['clasificacion_elasticidad'].eq('beta_positiva_revision').mean() * 100:.2f}%")
        print(f"  % elasticas: {df['clasificacion_elasticidad'].eq('elastico').mean() * 100:.2f}%")
        print(f"  % inelasticas: {df['clasificacion_elasticidad'].eq('inelastico').mean() * 100:.2f}%")

    print("Entrega elasticidad generada")
    print_stats("Modelo 1", model1)
    print_stats("Modelo 2", model2)
    print("Principales razones no calculables:")
    print(diag[diag["razon"] != "calculada"].groupby(["modelo", "razon"]).size().sort_values(ascending=False).head(10).to_string())
    print(f"salida modelo1: {model1_path}")
    print(f"salida modelo2: {model2_path}")
    print(f"salida excel: {xlsx_path}")
    print(f"graficas guardadas: {len(saved_graphs)} en {graph_dir}")
    print("SKUs graficados desde Base_OfficeMax19mayo:")
    if not selected_graph_skus.empty:
        print(selected_graph_skus.to_string(index=False))
    if saved_graphs:
        for graph in saved_graphs:
            print(f"  {graph}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
