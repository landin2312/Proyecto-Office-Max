from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def pct(value: float, denominator: float) -> float:
    return float(value / denominator * 100) if denominator else 0.0


def load_inputs(betas_path: Path, master_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    betas = pd.read_csv(betas_path, dtype={"SKU": str}, encoding="utf-8-sig")
    master = pd.read_csv(master_path, dtype={"prod_nbr": str}, encoding="utf-8-sig")
    betas["periodo_inicio"] = pd.to_datetime(betas["periodo_inicio"], errors="coerce")
    betas["periodo_fin"] = pd.to_datetime(betas["periodo_fin"], errors="coerce")
    betas["beta"] = pd.to_numeric(betas["beta"], errors="coerce")
    betas["r2"] = pd.to_numeric(betas["r2"], errors="coerce")
    betas["n_observaciones"] = pd.to_numeric(betas["n_observaciones"], errors="coerce")
    master["fecha"] = pd.to_datetime(master["fecha"], errors="coerce")
    master["precio"] = pd.to_numeric(master["precio"], errors="coerce")
    master["qty"] = pd.to_numeric(master["qty"], errors="coerce")
    return betas, master


def attach_window_variation(betas: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    needed = master[["prod_nbr", "fecha", "precio", "qty"]].copy()
    needed = needed[(needed["precio"] > 0) & (needed["qty"] > 0)].dropna()

    for sku, sku_betas in betas.groupby("SKU", sort=False):
        sku_master = needed[needed["prod_nbr"] == sku]
        rows = []
        for row in sku_betas.itertuples(index=False):
            window = sku_master[(sku_master["fecha"] >= row.periodo_inicio) & (sku_master["fecha"] <= row.periodo_fin)]
            rows.append(
                {
                    "idx": row.Index if hasattr(row, "Index") else None,
                    "precio_unique": int(window["precio"].nunique(dropna=True)),
                    "qty_unique": int(window["qty"].nunique(dropna=True)),
                    "n_valid_recalc": int(len(window)),
                }
            )
        part = sku_betas.reset_index().join(pd.DataFrame(rows).drop(columns=["idx"], errors="ignore"))
        pieces.append(part)

    enriched = pd.concat(pieces, ignore_index=True) if pieces else betas.reset_index()
    return enriched


def classify_rows(enriched: pd.DataFrame) -> pd.DataFrame:
    enriched = enriched.copy()
    enriched["beta_valida"] = (
        enriched["beta"].notna()
        & enriched["r2"].notna()
        & (enriched["n_observaciones"] >= 3)
        & (enriched["precio_unique"] >= 2)
        & (enriched["qty_unique"] >= 2)
    )

    conditions = [
        enriched["beta_valida"],
        enriched["n_observaciones"].fillna(0) < 3,
        enriched["precio_unique"].fillna(0) < 2,
        enriched["qty_unique"].fillna(0) < 2,
    ]
    choices = ["valida", "n<3", "precio constante", "qty constante"]
    enriched["razon_exclusion"] = np.select(conditions, choices, default="datos insuficientes")
    return enriched


def bucket_n_observaciones(value: float) -> str:
    if pd.isna(value):
        return "sin dato"
    value = int(value)
    if value < 3:
        return "0-2"
    if value <= 5:
        return "3-5"
    if value <= 10:
        return "6-10"
    if value <= 20:
        return "11-20"
    return "21+"


def bucket_r2(value: float) -> str:
    if pd.isna(value):
        return "sin R2"
    if value < 0.2:
        return "0.00-0.20"
    if value < 0.4:
        return "0.20-0.40"
    if value < 0.6:
        return "0.40-0.60"
    if value < 0.8:
        return "0.60-0.80"
    return "0.80-1.00"


def rows_from_counts(section: str, counts: pd.Series, denominator: int) -> list[dict[str, object]]:
    rows = []
    for metric, count in counts.items():
        rows.append(
            {
                "seccion": section,
                "metric": metric,
                "valor": count,
                "porcentaje": pct(float(count), denominator),
                "detalle": "",
            }
        )
    return rows


def build_diagnostic(enriched: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_skus = enriched["SKU"].nunique()
    monthly = enriched[enriched["tipo_ventana"] == "mensual"]
    monthly_valid_skus = monthly.loc[monthly["beta_valida"], "SKU"].nunique()
    rows.append(
        {
            "seccion": "resumen",
            "metric": "porcentaje_sku_con_beta_mensual_valida",
            "valor": monthly_valid_skus,
            "porcentaje": pct(monthly_valid_skus, total_skus),
            "detalle": f"{monthly_valid_skus} de {total_skus} SKU",
        }
    )

    valid_counts = enriched.groupby("tipo_ventana")["beta_valida"].agg(["size", "sum"]).reset_index()
    for row in valid_counts.itertuples(index=False):
        rows.append(
            {
                "seccion": "resumen_por_ventana",
                "metric": row.tipo_ventana,
                "valor": int(row.sum),
                "porcentaje": pct(float(row.sum), float(row.size)),
                "detalle": f"{int(row.sum)} validas de {int(row.size)} ventanas",
            }
        )

    n_counts = enriched["n_observaciones"].map(bucket_n_observaciones).value_counts().sort_index()
    rows.extend(rows_from_counts("distribucion_n_observaciones", n_counts, len(enriched)))

    r2_counts = enriched["r2"].map(bucket_r2).value_counts().sort_index()
    rows.extend(rows_from_counts("distribucion_r2", r2_counts, len(enriched)))

    invalid = enriched[~enriched["beta_valida"]]
    reason_counts = invalid["razon_exclusion"].value_counts()
    rows.extend(rows_from_counts("razones_exclusion", reason_counts, len(invalid)))

    sku_counts = (
        enriched.groupby("SKU")
        .agg(betas_validas=("beta_valida", "sum"), ventanas=("beta_valida", "size"))
        .reset_index()
    )
    sku_counts["porcentaje_validas"] = sku_counts["betas_validas"] / sku_counts["ventanas"] * 100
    top_more = sku_counts.sort_values(["betas_validas", "porcentaje_validas", "SKU"], ascending=[False, False, True]).head(20)
    top_less = sku_counts.sort_values(["betas_validas", "porcentaje_validas", "SKU"], ascending=[True, True, True]).head(20)

    for section, table in (("top_20_mas_betas_validas", top_more), ("top_20_menos_betas_validas", top_less)):
        for row in table.itertuples(index=False):
            rows.append(
                {
                    "seccion": section,
                    "metric": row.SKU,
                    "valor": int(row.betas_validas),
                    "porcentaje": float(row.porcentaje_validas),
                    "detalle": f"{int(row.betas_validas)} validas de {int(row.ventanas)} ventanas",
                }
            )

    return pd.DataFrame(rows, columns=["seccion", "metric", "valor", "porcentaje", "detalle"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostica betas dinamicas de elasticidad.")
    parser.add_argument("--betas", default=Path("output/elasticidad_dinamica_betas_sku_fecha.csv"), type=Path)
    parser.add_argument("--master", default=Path("output/MASTER_FINAL_SKU_FECHA.csv"), type=Path)
    parser.add_argument("--output", default=Path("output/diagnostico_betas.csv"), type=Path)
    args = parser.parse_args()

    betas, master = load_inputs(args.betas, args.master)
    enriched = classify_rows(attach_window_variation(betas, master))
    diagnostic = build_diagnostic(enriched)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    diagnostic.to_csv(args.output, index=False, encoding="utf-8-sig")

    monthly = enriched[enriched["tipo_ventana"] == "mensual"]
    monthly_valid_skus = monthly.loc[monthly["beta_valida"], "SKU"].nunique()
    total_skus = enriched["SKU"].nunique()
    print("Diagnostico betas")
    print(f"SKU con beta mensual valida: {monthly_valid_skus} de {total_skus} ({pct(monthly_valid_skus, total_skus):.2f}%)")
    print()
    print("Betas validas por ventana:")
    print(enriched.groupby("tipo_ventana")["beta_valida"].agg(total="size", validas="sum").to_string())
    print()
    print("Razones de exclusion:")
    invalid = enriched[~enriched["beta_valida"]]
    reason_counts = invalid["razon_exclusion"].value_counts()
    for reason, count in reason_counts.items():
        print(f"  {reason}: {count} ({pct(float(count), len(invalid)):.2f}%)")
    print(f"salida: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
