from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


COLORS = {
    "mensual": "#2563eb",
    "trimestral": "#059669",
    "semestral": "#dc2626",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida ventanas moviles y grafica beta temporal para un SKU.")
    parser.add_argument("--sku", default="50106204")
    parser.add_argument("--betas", default=Path("output/elasticidad_dinamica_betas_sku_fecha.csv"), type=Path)
    parser.add_argument("--output-csv", default=Path("output/validacion_ventanas_50106204.csv"), type=Path)
    parser.add_argument("--output-png", default=Path("output/beta_temporal_50106204.png"), type=Path)
    args = parser.parse_args()

    betas = pd.read_csv(args.betas, dtype={"SKU": str}, encoding="utf-8-sig")
    betas["periodo_inicio"] = pd.to_datetime(betas["periodo_inicio"], errors="coerce")
    betas["periodo_fin"] = pd.to_datetime(betas["periodo_fin"], errors="coerce")
    betas["beta"] = pd.to_numeric(betas["beta"], errors="coerce")
    betas["r2"] = pd.to_numeric(betas["r2"], errors="coerce")
    betas["n_observaciones"] = pd.to_numeric(betas["n_observaciones"], errors="coerce")

    sku_data = betas[betas["SKU"] == args.sku].sort_values(["tipo_ventana", "periodo_inicio"]).copy()
    output_cols = ["SKU", "tipo_ventana", "periodo_inicio", "periodo_fin", "beta", "r2", "n_observaciones"]
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    sku_data[output_cols].to_csv(args.output_csv, index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(11, 6))
    for window in ["mensual", "trimestral", "semestral"]:
        series = sku_data[sku_data["tipo_ventana"] == window].sort_values("periodo_inicio")
        valid = series[series["beta"].notna()]
        if valid.empty:
            continue
        ax.plot(
            valid["periodo_inicio"],
            valid["beta"],
            marker="o",
            linewidth=1.8,
            markersize=4,
            color=COLORS[window],
            label=window,
        )

    ax.axhline(0, color="#111827", linewidth=1, alpha=0.55)
    ax.set_title(f"Beta temporal por ventana - SKU {args.sku}")
    ax.set_xlabel("Periodo inicio")
    ax.set_ylabel("Beta ln(qty) ~ ln(price)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(args.output_png, dpi=150)
    plt.close(fig)

    print(f"SKU: {args.sku}")
    for window in ["mensual", "trimestral", "semestral"]:
        series = sku_data[sku_data["tipo_ventana"] == window].sort_values("periodo_inicio")
        print()
        print(window)
        print(series[["SKU", "periodo_inicio", "periodo_fin", "beta", "r2", "n_observaciones"]].head(12).to_string(index=False))
    print()
    print(f"salida CSV: {args.output_csv}")
    print(f"salida PNG: {args.output_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
