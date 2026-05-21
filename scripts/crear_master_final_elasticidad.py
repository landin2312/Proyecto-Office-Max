from __future__ import annotations

import argparse
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


def month_start(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.to_period("M").dt.to_timestamp()


def numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def discount_to_pct(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().lower().replace(",", ".")
    if not text:
        return np.nan
    if text == "2x1":
        return 50.0
    if text == "3x2":
        return 33.3333333333
    if text == "5x4":
        return 20.0
    cleaned = text.replace("%", "")
    try:
        number = float(cleaned)
    except ValueError:
        return np.nan
    return number if 0 <= number <= 100 else np.nan


def promo_month_from_row(row: pd.Series) -> pd.Timestamp | pd.NaT:
    for field in ("fecha_inicio", "fecha_comunicado"):
        value = pd.to_datetime(row.get(field), errors="coerce")
        if pd.notna(value):
            return value.to_period("M").to_timestamp()

    month_name = str(row.get("mes_carpeta", "")).strip().upper()
    month = MONTHS.get(month_name)
    if month:
        return pd.Timestamp(year=2024, month=month, day=1)
    return pd.NaT


def build_sales_monthly(ventas_path: Path) -> pd.DataFrame:
    ventas = read_csv(ventas_path)
    ventas["prod_nbr"] = clean_sku(ventas["prod_nbr"])
    ventas["fecha"] = month_start(ventas["tran_date"])
    ventas["qty"] = numeric(ventas["qty"])
    ventas["net_sale"] = numeric(ventas["net_sale"])
    ventas = ventas.dropna(subset=["prod_nbr", "fecha"])

    grouped = (
        ventas.groupby(["prod_nbr", "fecha"], as_index=False)
        .agg(unidades_vendidas=("qty", "sum"), venta_neta=("net_sale", "sum"))
    )
    grouped["precio_promedio"] = grouped["venta_neta"] / grouped["unidades_vendidas"].replace(0, np.nan)
    grouped.loc[grouped["precio_promedio"] <= 0, "precio_promedio"] = np.nan
    return grouped


def build_promo_monthly(promos_path: Path) -> pd.DataFrame:
    promos = read_csv(promos_path)
    promos["prod_nbr"] = clean_sku(promos["prod_nbr"])
    promos["fecha"] = promos.apply(promo_month_from_row, axis=1)
    promos["descuento_pct_num"] = promos["descuento_pct"].map(discount_to_pct)
    promos = promos.dropna(subset=["prod_nbr", "fecha"])

    return (
        promos.groupby(["prod_nbr", "fecha"], as_index=False)
        .agg(
            descuento_promedio=("descuento_pct_num", "mean"),
            promociones_detectadas=("promo_id", "nunique"),
        )
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
    price_dim = precios[["prod_nbr", "estimated_unit_price"]].drop_duplicates("prod_nbr")
    return products.merge(price_dim, on="prod_nbr", how="outer")


def build_master_final(
    ventas_path: Path,
    precios_path: Path,
    catalogo_path: Path,
    promos_path: Path,
) -> pd.DataFrame:
    sales = build_sales_monthly(ventas_path)
    promos = build_promo_monthly(promos_path)
    products = build_product_dimension(catalogo_path, precios_path)

    master = sales.merge(products, on="prod_nbr", how="left").merge(promos, on=["prod_nbr", "fecha"], how="left")
    master["indicador_promocion"] = (master["promociones_detectadas"].fillna(0).astype(float) > 0).astype(int)
    master["descuento_promedio"] = master["descuento_promedio"].fillna(0)
    master["precio_promedio"] = master["precio_promedio"].fillna(master["estimated_unit_price"])
    master["mes"] = master["fecha"].dt.strftime("%Y-%m")
    master = master.sort_values(["prod_nbr", "fecha"]).reset_index(drop=True)

    first_cols = [
        "prod_nbr",
        "fecha",
        "mes",
        "unidades_vendidas",
        "precio_promedio",
        "descuento_promedio",
        "indicador_promocion",
    ]
    other_cols = [col for col in master.columns if col not in first_cols]
    return master[first_cols + other_cols]


def slope_beta(window: pd.DataFrame) -> float:
    clean = window[["unidades_vendidas", "precio_promedio"]].dropna()
    clean = clean[(clean["unidades_vendidas"] > 0) & (clean["precio_promedio"] > 0)]
    if len(clean) < 2:
        return np.nan
    x = np.log(clean["precio_promedio"].to_numpy(dtype=float))
    y = np.log(clean["unidades_vendidas"].to_numpy(dtype=float))
    if np.isclose(np.var(x), 0):
        return np.nan
    return float(np.polyfit(x, y, 1)[0])


def build_dynamic_betas(master: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    needed = master[["prod_nbr", "fecha", "unidades_vendidas", "precio_promedio"]].copy()
    needed = needed.dropna(subset=["prod_nbr", "fecha"]).sort_values(["prod_nbr", "fecha"])

    for sku, group in needed.groupby("prod_nbr", sort=False):
        group = group.sort_values("fecha").reset_index(drop=True)
        for spec in WINDOWS:
            for end_pos in range(len(group)):
                end_date = group.loc[end_pos, "fecha"]
                start_date = (end_date.to_period("M") - (spec.months - 1)).to_timestamp()
                window = group[(group["fecha"] >= start_date) & (group["fecha"] <= end_date)]
                rows.append(
                    {
                        "SKU": sku,
                        "periodo_inicio": start_date.date().isoformat(),
                        "periodo_fin": end_date.date().isoformat(),
                        "tipo_ventana": spec.name,
                        "beta": slope_beta(window),
                    }
                )
    return pd.DataFrame(rows, columns=["SKU", "periodo_inicio", "periodo_fin", "tipo_ventana", "beta"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea MASTER_FINAL SKU-MES y betas dinamicas de elasticidad.")
    parser.add_argument("--ventas", default=Path("Ventas_2024_2026 - Ventas_2024_2026.csv"), type=Path)
    parser.add_argument("--precios", default=Path("Precios_Producto - Precios_Producto.csv"), type=Path)
    parser.add_argument("--catalogo", default=Path("Catalogo_Producto - Catalogo_Producto.csv"), type=Path)
    parser.add_argument("--promos", default=Path("output/promociones_master.csv"), type=Path)
    parser.add_argument("--output-dir", default=Path("output"), type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    master = build_master_final(args.ventas, args.precios, args.catalogo, args.promos)
    betas = build_dynamic_betas(master)

    master_path = args.output_dir / "MASTER_FINAL_SKU_MES.csv"
    betas_path = args.output_dir / "elasticidad_dinamica_betas.csv"
    master.to_csv(master_path, index=False, encoding="utf-8-sig")
    betas.to_csv(betas_path, index=False, encoding="utf-8-sig")

    beta_valid = int(betas["beta"].notna().sum())
    print("MASTER_FINAL SKU-MES")
    print(f"filas master: {len(master)}")
    print(f"SKUs master: {master['prod_nbr'].nunique()}")
    print(f"meses master: {master['mes'].nunique()}")
    print(f"filas con promocion: {int(master['indicador_promocion'].sum())}")
    print(f"salida master: {master_path}")
    print()
    print("Elasticidad dinamica")
    print(f"filas beta: {len(betas)}")
    print(f"betas calculables: {beta_valid}")
    print(f"salida betas: {betas_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
