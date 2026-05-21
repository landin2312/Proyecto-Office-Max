from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WindowSpec:
    name: str
    months: int


WINDOWS = [
    WindowSpec("mensual", 1),
    WindowSpec("trimestral", 3),
    WindowSpec("semestral", 6),
]


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")


def clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def load_base(path: Path, dept: str | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df["fecha"] = pd.to_datetime(df["tran_date"], dayfirst=True, errors="coerce")
    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    df["prod_nbr"] = clean_text(df["prod_nbr"])
    df["store_nbr"] = clean_text(df["store_nbr"])
    df["dept_nm"] = clean_text(df["dept_nm"])
    df["subdept_nm"] = clean_text(df["subdept_nm"])
    df["class_nm"] = clean_text(df["class_nm"])
    df["qty"] = numeric(df["qty"])
    df["precio"] = numeric(df["precio"])
    df["net_sale"] = numeric(df["net_sale"])
    df["venta_con_iva"] = numeric(df["venta_con_iva"])
    df["utilidad"] = numeric(df["utilidad"])
    df["margen"] = numeric(df["margen"])

    if dept:
        df = df[df["dept_nm"].str.upper() == dept.strip().upper()].copy()

    return df.dropna(subset=["fecha", "prod_nbr", "store_nbr", "qty", "precio"])


def build_master_sku_store_month(df: pd.DataFrame) -> pd.DataFrame:
    dims = [
        "prod_nbr",
        "store_nbr",
        "mes",
        "dept_nm",
        "subdept_nm",
        "class_nm",
        "marca",
        "tipo_marca",
        "vendor_nm",
    ]
    grouped = (
        df.groupby(dims, dropna=False, as_index=False)
        .agg(
            qty=("qty", "sum"),
            net_sale=("net_sale", "sum"),
            venta_con_iva=("venta_con_iva", "sum"),
            utilidad=("utilidad", "sum"),
            margen=("margen", "mean"),
            precio_promedio=("precio", "mean"),
            transacciones=("tran_nbr", "nunique"),
            fechas_venta=("fecha", "nunique"),
        )
    )
    grouped["fecha_mes"] = pd.to_datetime(grouped["mes"] + "-01", errors="coerce")
    grouped["precio"] = grouped["net_sale"] / grouped["qty"].replace(0, np.nan)
    grouped["precio"] = grouped["precio"].fillna(grouped["precio_promedio"])
    grouped = grouped[(grouped["qty"] > 0) & (grouped["precio"] > 0)].copy()
    return grouped.sort_values(["prod_nbr", "store_nbr", "fecha_mes"]).reset_index(drop=True)


def regression(window: pd.DataFrame) -> tuple[float, float, int, str]:
    clean = window[["qty", "precio"]].dropna()
    clean = clean[(clean["qty"] > 0) & (clean["precio"] > 0)]
    n = len(clean)
    if n < 3:
        return np.nan, np.nan, n, "n<3"
    if clean["precio"].nunique() < 2:
        return np.nan, np.nan, n, "precio constante"
    if clean["qty"].nunique() < 2:
        return np.nan, np.nan, n, "qty constante"

    x = np.log(clean["precio"].to_numpy(dtype=float))
    y = np.log(clean["qty"].to_numpy(dtype=float))
    if np.isclose(np.var(x), 0):
        return np.nan, np.nan, n, "precio constante"
    beta, alpha = np.polyfit(x, y, 1)
    pred = alpha + beta * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = np.nan if np.isclose(ss_tot, 0) else 1 - ss_res / ss_tot
    if pd.isna(r2):
        return np.nan, np.nan, n, "qty constante"
    return float(beta), float(r2), n, "valida"


def build_betas(master: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    master = master.copy()
    master["period"] = master["fecha_mes"].dt.to_period("M")
    for sku, group in master.groupby("prod_nbr", sort=False):
        min_month = group["period"].min()
        max_month = group["period"].max()
        months = pd.period_range(min_month, max_month, freq="M")
        for spec in WINDOWS:
            for start_month in months:
                end_month = start_month + (spec.months - 1)
                if end_month > max_month:
                    continue
                start = start_month.to_timestamp()
                end = end_month.to_timestamp(how="end").normalize()
                window = group[(group["fecha_mes"] >= start) & (group["fecha_mes"] <= end)]
                beta, r2, n_obs, status = regression(window)
                rows.append(
                    {
                        "SKU": sku,
                        "periodo_inicio": start.date().isoformat(),
                        "periodo_fin": end.date().isoformat(),
                        "tipo_ventana": spec.name,
                        "beta": beta,
                        "r2": r2,
                        "n_observaciones": n_obs,
                        "estatus_beta": status,
                    }
                )
    return pd.DataFrame(rows)


def build_diagnostic(betas: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_skus = betas["SKU"].nunique()
    monthly = betas[betas["tipo_ventana"] == "mensual"]
    monthly_valid_skus = monthly.loc[monthly["estatus_beta"] == "valida", "SKU"].nunique()
    rows.append(
        {
            "seccion": "resumen",
            "metric": "sku_con_beta_mensual_valida",
            "valor": monthly_valid_skus,
            "porcentaje": monthly_valid_skus / total_skus * 100 if total_skus else 0,
            "detalle": f"{monthly_valid_skus} de {total_skus} SKU",
        }
    )
    for window, group in betas.groupby("tipo_ventana"):
        valid = int((group["estatus_beta"] == "valida").sum())
        rows.append(
            {
                "seccion": "resumen_por_ventana",
                "metric": window,
                "valor": valid,
                "porcentaje": valid / len(group) * 100 if len(group) else 0,
                "detalle": f"{valid} validas de {len(group)} ventanas",
            }
        )
    invalid = betas[betas["estatus_beta"] != "valida"]
    for reason, count in invalid["estatus_beta"].value_counts().items():
        rows.append(
            {
                "seccion": "razones_exclusion",
                "metric": reason,
                "valor": int(count),
                "porcentaje": count / len(invalid) * 100 if len(invalid) else 0,
                "detalle": "",
            }
        )
    sku_counts = (
        betas.groupby("SKU")
        .agg(betas_validas=("estatus_beta", lambda s: int((s == "valida").sum())), ventanas=("estatus_beta", "size"))
        .reset_index()
    )
    sku_counts["porcentaje"] = sku_counts["betas_validas"] / sku_counts["ventanas"] * 100
    for section, table in [
        ("top_20_mas_betas_validas", sku_counts.sort_values(["betas_validas", "porcentaje"], ascending=False).head(20)),
        ("top_20_menos_betas_validas", sku_counts.sort_values(["betas_validas", "porcentaje"], ascending=True).head(20)),
    ]:
        for row in table.itertuples(index=False):
            rows.append(
                {
                    "seccion": section,
                    "metric": row.SKU,
                    "valor": int(row.betas_validas),
                    "porcentaje": float(row.porcentaje),
                    "detalle": f"{int(row.betas_validas)} validas de {int(row.ventanas)} ventanas",
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Modelo de elasticidad dinamica para Base_OfficeMax19mayo.")
    parser.add_argument("--input", default=Path("Base_OfficeMax19mayo.csv"), type=Path)
    parser.add_argument("--output-dir", default=Path("output/base19mayo"), type=Path)
    parser.add_argument("--dept", default=None, help="Opcional: filtrar dept_nm exacto.")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_base(args.input, dept=args.dept)
    master = build_master_sku_store_month(df)
    betas = build_betas(master)
    diagnostic = build_diagnostic(betas)

    suffix = "" if not args.dept else "_" + args.dept.strip().upper().replace(" ", "_")
    master_path = args.output_dir / f"MASTER_SKU_TIENDA_MES{suffix}.csv"
    betas_path = args.output_dir / f"betas_dinamicas{suffix}.csv"
    diagnostic_path = args.output_dir / f"diagnostico_betas{suffix}.csv"
    master.to_csv(master_path, index=False, encoding="utf-8-sig")
    betas.to_csv(betas_path, index=False, encoding="utf-8-sig")
    diagnostic.to_csv(diagnostic_path, index=False, encoding="utf-8-sig")

    print("Modelo Base_OfficeMax19mayo")
    print(f"departamento: {args.dept or 'TODOS'}")
    print(f"filas base filtrada: {len(df)}")
    print(f"filas master SKU-tienda-mes: {len(master)}")
    print(f"SKUs: {master['prod_nbr'].nunique()}")
    print(f"tiendas: {master['store_nbr'].nunique()}")
    print(f"meses: {master['mes'].nunique()}")
    print("betas validas por ventana:")
    print(betas.groupby("tipo_ventana")["estatus_beta"].apply(lambda s: int((s == "valida").sum())).to_string())
    print(f"salida master: {master_path}")
    print(f"salida betas: {betas_path}")
    print(f"salida diagnostico: {diagnostic_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
