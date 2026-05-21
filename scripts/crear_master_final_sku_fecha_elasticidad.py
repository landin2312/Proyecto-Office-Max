from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


MONTHS = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "SETIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}


@dataclass(frozen=True)
class WindowSpec:
    name: str
    months: int


WINDOWS = [
    WindowSpec("mensual", 1),
    WindowSpec("trimestral", 3),
    WindowSpec("semestral", 6),
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig")


def clean_sku(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def discount_to_pct(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().lower().replace(",", ".")
    if not text:
        return np.nan
    combos = {"2x1": 50.0, "3x2": 33.3333333333, "5x4": 20.0}
    if text in combos:
        return combos[text]
    try:
        number = float(text.replace("%", ""))
    except ValueError:
        return np.nan
    return number if 0 <= number <= 100 else np.nan


def month_bounds(month_name: object, year: int = 2024) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    month = MONTHS.get(str(month_name).strip().upper())
    if not month:
        return None
    last_day = calendar.monthrange(year, month)[1]
    return pd.Timestamp(year=year, month=month, day=1), pd.Timestamp(year=year, month=month, day=last_day)


def promo_bounds(row: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    start = pd.to_datetime(row.get("fecha_inicio"), errors="coerce")
    end = pd.to_datetime(row.get("fecha_fin"), errors="coerce")
    communicated = pd.to_datetime(row.get("fecha_comunicado"), errors="coerce")

    if pd.notna(start) and pd.notna(end):
        return start.normalize(), end.normalize()
    if pd.notna(start):
        return start.normalize(), start.normalize()
    if pd.notna(communicated):
        return communicated.normalize(), communicated.normalize()
    return month_bounds(row.get("mes_carpeta"))


def build_sales_daily(ventas_path: Path) -> pd.DataFrame:
    ventas = read_csv(ventas_path)
    ventas["prod_nbr"] = clean_sku(ventas["prod_nbr"])
    ventas["fecha"] = pd.to_datetime(ventas["tran_date"], errors="coerce").dt.normalize()
    ventas["qty"] = numeric(ventas["qty"])
    ventas["net_sale"] = numeric(ventas["net_sale"])
    ventas = ventas.dropna(subset=["prod_nbr", "fecha"])

    daily = (
        ventas.groupby(["prod_nbr", "fecha"], as_index=False)
        .agg(qty=("qty", "sum"), venta_neta=("net_sale", "sum"), transacciones=("qty", "size"))
    )
    daily["precio"] = daily["venta_neta"] / daily["qty"].replace(0, np.nan)
    daily.loc[daily["precio"] <= 0, "precio"] = np.nan
    return daily


def build_promo_daily(promos_path: Path) -> pd.DataFrame:
    promos = read_csv(promos_path)
    promos["prod_nbr"] = clean_sku(promos["prod_nbr"])
    promos["descuento_num"] = promos["descuento_pct"].map(discount_to_pct)
    promos = promos.dropna(subset=["prod_nbr"])

    rows: list[dict[str, object]] = []
    for row in promos.itertuples(index=False):
        row_series = pd.Series(row._asdict())
        bounds = promo_bounds(row_series)
        if bounds is None:
            continue
        start, end = bounds
        if pd.isna(start) or pd.isna(end) or end < start:
            continue
        for fecha in pd.date_range(start, end, freq="D"):
            rows.append(
                {
                    "prod_nbr": row_series.get("prod_nbr"),
                    "fecha": fecha,
                    "descuento": row_series.get("descuento_num"),
                    "promo_id": row_series.get("promo_id"),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["prod_nbr", "fecha", "descuento", "promociones_detectadas"])

    promo_daily = pd.DataFrame(rows)
    return (
        promo_daily.groupby(["prod_nbr", "fecha"], as_index=False)
        .agg(descuento=("descuento", "mean"), promociones_detectadas=("promo_id", "nunique"))
    )


def build_product_dimension(catalogo_path: Path, precios_path: Path) -> pd.DataFrame:
    catalogo = read_csv(catalogo_path)
    precios = read_csv(precios_path)
    catalogo["prod_nbr"] = clean_sku(catalogo["prod_nbr"])
    precios["prod_nbr"] = clean_sku(precios["prod_nbr"])
    precios["estimated_unit_price"] = numeric(precios["estimated_unit_price"])

    catalog_cols = [
        "prod_nbr",
        "prod_nm",
        "dept_cd",
        "dept_nm",
        "subdept_cd",
        "subdept_nm",
        "class_cd",
        "class_nm",
        "vendor_nbr",
        "vendor_nm",
        "marca_fabricante",
        "tipo_marca",
    ]
    catalog_cols = [col for col in catalog_cols if col in catalogo.columns]
    products = catalogo[catalog_cols].drop_duplicates("prod_nbr")
    prices = precios[["prod_nbr", "estimated_unit_price"]].drop_duplicates("prod_nbr")
    return products.merge(prices, on="prod_nbr", how="outer")


def build_master_final(
    ventas_path: Path,
    precios_path: Path,
    catalogo_path: Path,
    promos_path: Path,
) -> pd.DataFrame:
    sales = build_sales_daily(ventas_path)
    promo_daily = build_promo_daily(promos_path)
    products = build_product_dimension(catalogo_path, precios_path)

    master = sales.merge(products, on="prod_nbr", how="left").merge(promo_daily, on=["prod_nbr", "fecha"], how="left")
    master["promocion"] = (master["promociones_detectadas"].fillna(0).astype(float) > 0).astype(int)
    master["descuento"] = master["descuento"].fillna(0)
    master["precio"] = master["precio"].fillna(master["estimated_unit_price"])
    master["mes"] = master["fecha"].dt.to_period("M").astype(str)
    master = master.sort_values(["prod_nbr", "fecha"]).reset_index(drop=True)

    first_cols = ["prod_nbr", "fecha", "mes", "precio", "qty", "promocion", "descuento"]
    other_cols = [col for col in master.columns if col not in first_cols]
    return master[first_cols + other_cols]


def regression_stats(window: pd.DataFrame) -> tuple[float, float, int]:
    clean = window[["qty", "precio"]].dropna()
    clean = clean[(clean["qty"] > 0) & (clean["precio"] > 0)]
    n = len(clean)
    if n < 2:
        return np.nan, np.nan, n

    x = np.log(clean["precio"].to_numpy(dtype=float))
    y = np.log(clean["qty"].to_numpy(dtype=float))
    if np.isclose(np.var(x), 0):
        return np.nan, np.nan, n

    beta, alpha = np.polyfit(x, y, 1)
    predicted = alpha + beta * x
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = np.nan if np.isclose(ss_tot, 0) else 1 - ss_res / ss_tot
    return float(beta), float(r2), n


def month_window(month: pd.Period, months: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = month.to_timestamp()
    end = (month + (months - 1)).to_timestamp(how="end").normalize()
    return start, end


def build_dynamic_betas(master: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    data = master[["prod_nbr", "fecha", "qty", "precio"]].dropna(subset=["prod_nbr", "fecha"]).copy()
    data = data.sort_values(["prod_nbr", "fecha"])
    data["month_period"] = data["fecha"].dt.to_period("M")

    for sku, group in data.groupby("prod_nbr", sort=False):
        months = pd.period_range(group["month_period"].min(), group["month_period"].max(), freq="M")
        for spec in WINDOWS:
            for month in months:
                start, end = month_window(month, spec.months)
                if end > group["fecha"].max().to_period("M").to_timestamp(how="end").normalize():
                    continue
                window = group[(group["fecha"] >= start) & (group["fecha"] <= end)]
                if window.empty:
                    continue
                beta, r2, n_obs = regression_stats(window)
                rows.append(
                    {
                        "SKU": sku,
                        "periodo_inicio": start.date().isoformat(),
                        "periodo_fin": end.date().isoformat(),
                        "tipo_ventana": spec.name,
                        "beta": beta,
                        "r2": r2,
                        "n_observaciones": n_obs,
                    }
                )

    return pd.DataFrame(
        rows,
        columns=["SKU", "periodo_inicio", "periodo_fin", "tipo_ventana", "beta", "r2", "n_observaciones"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea MASTER_FINAL SKU-FECHA y betas dinamicas de elasticidad.")
    parser.add_argument("--ventas", default=Path("Ventas_2024_2026 - Ventas_2024_2026.csv"), type=Path)
    parser.add_argument("--precios", default=Path("Precios_Producto - Precios_Producto.csv"), type=Path)
    parser.add_argument("--catalogo", default=Path("Catalogo_Producto - Catalogo_Producto.csv"), type=Path)
    parser.add_argument("--promos", default=Path("output/promociones_master.csv"), type=Path)
    parser.add_argument("--output-dir", default=Path("output"), type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    master = build_master_final(args.ventas, args.precios, args.catalogo, args.promos)
    betas = build_dynamic_betas(master)

    master_path = args.output_dir / "MASTER_FINAL_SKU_FECHA.csv"
    betas_path = args.output_dir / "elasticidad_dinamica_betas_sku_fecha.csv"
    master.to_csv(master_path, index=False, encoding="utf-8-sig")
    betas.to_csv(betas_path, index=False, encoding="utf-8-sig")

    summary = betas.groupby("tipo_ventana")["beta"].agg(filas="size", betas_calculables="count")
    monthly_valid = int(summary.loc["mensual", "betas_calculables"]) if "mensual" in summary.index else 0

    print("MASTER_FINAL SKU-FECHA")
    print(f"filas master: {len(master)}")
    print(f"SKUs master: {master['prod_nbr'].nunique()}")
    print(f"fechas master: {master['fecha'].nunique()}")
    print(f"rango fecha: {master['fecha'].min().date().isoformat()} a {master['fecha'].max().date().isoformat()}")
    print(f"filas con promocion: {int(master['promocion'].sum())}")
    print(f"salida master: {master_path}")
    print()
    print("Elasticidad dinamica")
    print(summary.to_string())
    print(f"betas mensuales calculables: {monthly_valid}")
    print(f"salida betas: {betas_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
