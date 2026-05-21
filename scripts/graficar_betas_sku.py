from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


WINDOW_ORDER = ["mensual", "trimestral", "semestral"]
WINDOW_COLORS = {
    "mensual": "#2563eb",
    "trimestral": "#059669",
    "semestral": "#dc2626",
}


def read_skus(diagnostic_path: Path, limit: int) -> list[str]:
    diagnostic = pd.read_csv(diagnostic_path, dtype={"metric": str}, encoding="utf-8-sig")
    top = diagnostic[diagnostic["seccion"] == "top_20_mas_betas_validas"].copy()
    top["valor"] = pd.to_numeric(top["valor"], errors="coerce")
    return top.sort_values("valor", ascending=False)["metric"].head(limit).tolist()


def valid_betas(betas_path: Path, skus: list[str]) -> pd.DataFrame:
    betas = pd.read_csv(betas_path, dtype={"SKU": str}, encoding="utf-8-sig")
    betas["periodo_fin"] = pd.to_datetime(betas["periodo_fin"], errors="coerce")
    betas["beta"] = pd.to_numeric(betas["beta"], errors="coerce")
    betas["r2"] = pd.to_numeric(betas["r2"], errors="coerce")
    betas["n_observaciones"] = pd.to_numeric(betas["n_observaciones"], errors="coerce")
    filtered = betas[betas["SKU"].isin(skus)].copy()
    return filtered[
        filtered["beta"].notna()
        & filtered["r2"].notna()
        & (filtered["n_observaciones"] >= 3)
    ].sort_values(["SKU", "tipo_ventana", "periodo_fin"])


def plot_sku(sku: str, sku_data: pd.DataFrame, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6))
    for window in WINDOW_ORDER:
        series = sku_data[sku_data["tipo_ventana"] == window].sort_values("periodo_fin")
        if series.empty:
            continue
        ax.plot(
            series["periodo_fin"],
            series["beta"],
            marker="o",
            linewidth=1.8,
            markersize=4,
            color=WINDOW_COLORS[window],
            label=window,
        )

    ax.axhline(0, color="#111827", linewidth=1, alpha=0.55)
    ax.set_title(f"Elasticidad dinamica beta - SKU {sku}")
    ax.set_xlabel("Periodo fin")
    ax.set_ylabel("Beta ln(qty) ~ ln(price)")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()

    path = output_dir / f"beta_sku_{sku}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def detect_changes(data: pd.DataFrame, delta_threshold: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (sku, window), group in data.groupby(["SKU", "tipo_ventana"], sort=False):
        group = group.sort_values("periodo_fin").reset_index(drop=True)
        previous = None
        for row in group.itertuples(index=False):
            if previous is None:
                previous = row
                continue
            delta = float(row.beta - previous.beta)
            sign_change = (row.beta > 0 and previous.beta < 0) or (row.beta < 0 and previous.beta > 0)
            important = abs(delta) >= delta_threshold or sign_change
            if important:
                reasons = []
                if abs(delta) >= delta_threshold:
                    reasons.append(f"delta_abs>={delta_threshold:g}")
                if sign_change:
                    reasons.append("cambio_signo")
                rows.append(
                    {
                        "SKU": sku,
                        "tipo_ventana": window,
                        "periodo_anterior": previous.periodo_fin.date().isoformat(),
                        "periodo_actual": row.periodo_fin.date().isoformat(),
                        "beta_anterior": previous.beta,
                        "beta_actual": row.beta,
                        "delta_beta": delta,
                        "r2_actual": row.r2,
                        "n_observaciones_actual": int(row.n_observaciones),
                        "razon_cambio": "; ".join(reasons),
                    }
                )
            previous = row
    return pd.DataFrame(
        rows,
        columns=[
            "SKU",
            "tipo_ventana",
            "periodo_anterior",
            "periodo_actual",
            "beta_anterior",
            "beta_actual",
            "delta_beta",
            "r2_actual",
            "n_observaciones_actual",
            "razon_cambio",
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Grafica betas por SKU y detecta cambios importantes.")
    parser.add_argument("--diagnostico", default=Path("output/diagnostico_betas.csv"), type=Path)
    parser.add_argument("--betas", default=Path("output/elasticidad_dinamica_betas_sku_fecha.csv"), type=Path)
    parser.add_argument("--output-dir", default=Path("output/graficas_betas"), type=Path)
    parser.add_argument("--cambios-output", default=Path("output/cambios_importantes_betas.csv"), type=Path)
    parser.add_argument("--limit", default=20, type=int)
    parser.add_argument("--delta-threshold", default=1.0, type=float)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    skus = read_skus(args.diagnostico, args.limit)
    data = valid_betas(args.betas, skus)

    paths = []
    for sku in skus:
        sku_data = data[data["SKU"] == sku]
        if sku_data.empty:
            continue
        paths.append(plot_sku(sku, sku_data, args.output_dir))

    changes = detect_changes(data, args.delta_threshold)
    changes.to_csv(args.cambios_output, index=False, encoding="utf-8-sig")

    print("Graficas de betas")
    print(f"SKUs solicitados: {len(skus)}")
    print(f"graficas generadas: {len(paths)}")
    print(f"directorio: {args.output_dir}")
    print(f"cambios importantes detectados: {len(changes)}")
    print(f"salida cambios: {args.cambios_output}")
    if not changes.empty:
        print()
        print("Top cambios por magnitud:")
        preview = changes.assign(abs_delta=changes["delta_beta"].abs()).sort_values("abs_delta", ascending=False).head(20)
        for row in preview.itertuples(index=False):
            print(
                f"{row.SKU} {row.tipo_ventana} {row.periodo_anterior}->{row.periodo_actual}: "
                f"{row.beta_anterior:.3f} a {row.beta_actual:.3f} "
                f"(delta {row.delta_beta:.3f}, {row.razon_cambio})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
