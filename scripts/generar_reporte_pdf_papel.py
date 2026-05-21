from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


def add_title_page(pdf: PdfPages, summary: dict[str, object]) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.5, 0.86, "Elasticidad Dinamica - Departamento Papel", ha="center", fontsize=24, fontweight="bold")
    ax.text(0.5, 0.79, "Modelo de betas por ventanas moviles", ha="center", fontsize=15)

    lines = [
        f"Filas SKU-FECHA: {summary['filas_master']:,}",
        f"SKUs Papel: {summary['skus']:,}",
        f"Fechas: {summary['fechas']:,}",
        f"Filas con promocion: {summary['promos']:,}",
        "",
        "Ventanas usadas:",
        "Mensual: 1, 2, 3, 4",
        "Trimestral: 1-3, 2-4, 3-5, 4-6",
        "Semestral: 1-6, 2-7, 3-8, 4-9",
        "",
        "Regresion estimada:",
        "ln(qty) ~ ln(price)",
    ]
    ax.text(0.16, 0.66, "\n".join(lines), fontsize=13, va="top")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_table_page(pdf: PdfPages, title: str, df: pd.DataFrame, font_size: int = 10) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.02, 0.96, title, fontsize=18, fontweight="bold", va="top")
    table = ax.table(
        cellText=df.astype(str).values,
        colLabels=df.columns,
        loc="upper left",
        cellLoc="left",
        colLoc="left",
        bbox=[0.02, 0.08, 0.96, 0.82],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    for (row, _col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(fontweight="bold", color="white")
            cell.set_facecolor("#1f2937")
        else:
            cell.set_facecolor("#ffffff" if row % 2 else "#f3f4f6")
        cell.set_edgecolor("#d1d5db")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_image_page(pdf: PdfPages, image_path: Path, title: str) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.02, 0.97, title, fontsize=16, fontweight="bold", va="top")
    img = mpimg.imread(image_path)
    ax.imshow(img, extent=[0.04, 0.96, 0.06, 0.90], aspect="auto")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_bar_page(pdf: PdfPages, title: str, labels: list[str], values: list[float], ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.bar(labels, values, color="#2563eb")
    ax.set_title(title, fontsize=18, fontweight="bold", loc="left")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=25)
    for i, value in enumerate(values):
        ax.text(i, value, f"{value:,.2f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_hist_page(pdf: PdfPages, title: str, series: pd.Series, xlabel: str, bins: int = 35) -> None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.hist(clean, bins=bins, color="#2563eb", alpha=0.82, edgecolor="white")
    ax.axvline(clean.median(), color="#dc2626", linewidth=2, label=f"Mediana {clean.median():.2f}")
    ax.set_title(title, fontsize=18, fontweight="bold", loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frecuencia")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_heatmap_page(
    pdf: PdfPages,
    title: str,
    matrix: pd.DataFrame,
    cbar_label: str,
    cmap: str = "RdBu_r",
    center_zero: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(11, 8.5))
    values = matrix.to_numpy(dtype=float)
    if center_zero:
        vmax = np.nanmax(np.abs(values)) if np.isfinite(values).any() else 1
        vmin = -vmax
    else:
        vmin = np.nanmin(values) if np.isfinite(values).any() else 0
        vmax = np.nanmax(values) if np.isfinite(values).any() else 1
    image = ax.imshow(values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title, fontsize=18, fontweight="bold", loc="left")
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index)
    ax.set_xlabel("Mes")
    ax.set_ylabel("Año")
    fig.colorbar(image, ax=ax, label=cbar_label, shrink=0.75)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_scatter_page(pdf: PdfPages, title: str, df: pd.DataFrame) -> None:
    plot = df[(df["precio"] > 0) & (df["qty"] > 0)].copy()
    plot["log_precio"] = np.log(plot["precio"])
    plot["log_qty"] = np.log(plot["qty"])
    fig, ax = plt.subplots(figsize=(11, 8.5))
    no_promo = plot[plot["promocion"] == 0]
    promo = plot[plot["promocion"] > 0]
    ax.scatter(no_promo["log_precio"], no_promo["log_qty"], s=18, alpha=0.35, color="#2563eb", label="Sin promocion")
    ax.scatter(promo["log_precio"], promo["log_qty"], s=28, alpha=0.75, color="#dc2626", label="Con promocion")
    ax.set_title(title, fontsize=18, fontweight="bold", loc="left")
    ax.set_xlabel("ln(precio)")
    ax.set_ylabel("ln(qty)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_promo_comparison_page(pdf: PdfPages, master: pd.DataFrame) -> None:
    agg = (
        master.assign(promocion_label=np.where(master["promocion"] > 0, "Con promocion", "Sin promocion"))
        .groupby("promocion_label")
        .agg(precio_promedio=("precio", "mean"), qty_promedio=("qty", "mean"), filas=("qty", "size"))
        .reset_index()
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    axes[0].bar(agg["promocion_label"], agg["precio_promedio"], color=["#2563eb", "#dc2626"])
    axes[0].set_title("Precio promedio")
    axes[0].grid(axis="y", alpha=0.25)
    axes[1].bar(agg["promocion_label"], agg["qty_promedio"], color=["#2563eb", "#dc2626"])
    axes[1].set_title("Qty promedio")
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle("Comparativo con promocion vs sin promocion", fontsize=18, fontweight="bold")
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_insights_page(pdf: PdfPages, insights: list[str]) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.02, 0.96, "Insights principales para Papel", fontsize=20, fontweight="bold", va="top")
    text = "\n\n".join(f"{i + 1}. {insight}" for i, insight in enumerate(insights))
    ax.text(0.04, 0.86, text, fontsize=13, va="top", wrap=True)
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def diagnostic_table(diagnostic: pd.DataFrame, section: str, columns: list[str] | None = None) -> pd.DataFrame:
    table = diagnostic[diagnostic["seccion"] == section].copy()
    if columns:
        table = table[columns]
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera reporte PDF estatico para elasticidad de Papel.")
    parser.add_argument("--master", default=Path("output/MASTER_FINAL_SKU_FECHA_PAPEL.csv"), type=Path)
    parser.add_argument("--diagnostico", default=Path("output/diagnostico_betas_papel.csv"), type=Path)
    parser.add_argument("--resumen-cambios", default=Path("output/resumen_cambios_betas_papel.csv"), type=Path)
    parser.add_argument("--graficas-dir", default=Path("output/graficas_betas_papel"), type=Path)
    parser.add_argument("--output", default=Path("output/reporte_elasticidad_papel.pdf"), type=Path)
    parser.add_argument("--max-graficas", default=20, type=int)
    args = parser.parse_args()

    master = pd.read_csv(args.master, dtype={"prod_nbr": str}, encoding="utf-8-sig")
    betas = pd.read_csv("output/elasticidad_dinamica_betas_papel.csv", dtype={"SKU": str}, encoding="utf-8-sig")
    diagnostic = pd.read_csv(args.diagnostico, dtype={"metric": str}, encoding="utf-8-sig")
    cambios = pd.read_csv(args.resumen_cambios, dtype={"SKU": str}, encoding="utf-8-sig")
    for col in ["precio", "qty", "promocion", "descuento"]:
        master[col] = pd.to_numeric(master[col], errors="coerce")
    master["fecha"] = pd.to_datetime(master["fecha"], errors="coerce")
    for col in ["beta", "r2", "n_observaciones"]:
        betas[col] = pd.to_numeric(betas[col], errors="coerce")
    betas["periodo_inicio"] = pd.to_datetime(betas["periodo_inicio"], errors="coerce")
    betas["anio"] = betas["periodo_inicio"].dt.year
    betas["mes"] = betas["periodo_inicio"].dt.month

    summary = {
        "filas_master": len(master),
        "skus": master["prod_nbr"].nunique(),
        "fechas": master["fecha"].nunique(),
        "promos": int(pd.to_numeric(master["promocion"], errors="coerce").fillna(0).sum()),
    }

    resumen_ventana = diagnostic[diagnostic["seccion"] == "resumen_por_ventana"].copy()
    resumen_ventana = resumen_ventana.rename(columns={"metric": "ventana", "valor": "betas_validas", "porcentaje": "% valido", "detalle": "detalle"})
    resumen_ventana = resumen_ventana[["ventana", "betas_validas", "% valido", "detalle"]]
    resumen_ventana["% valido"] = resumen_ventana["% valido"].map(lambda x: f"{float(x):.2f}%")

    razones = diagnostic[diagnostic["seccion"] == "razones_exclusion"].copy()
    razones = razones.rename(columns={"metric": "razon", "valor": "ventanas", "porcentaje": "%"})
    razones = razones[["razon", "ventanas", "%"]]
    razones["%"] = razones["%"].map(lambda x: f"{float(x):.2f}%")

    top_skus = diagnostic[diagnostic["seccion"] == "top_20_mas_betas_validas"].copy()
    top_skus = top_skus.rename(columns={"metric": "SKU", "valor": "betas_validas", "porcentaje": "% validas"})
    top_skus = top_skus[["SKU", "betas_validas", "% validas", "detalle"]]
    top_skus["% validas"] = top_skus["% validas"].map(lambda x: f"{float(x):.2f}%")

    cambios_top = cambios.head(20).copy()
    cambios_top["max_abs_delta"] = cambios_top["max_abs_delta"].map(lambda x: f"{float(x):.2f}")
    cambios_top["mediana_abs_delta"] = cambios_top["mediana_abs_delta"].map(lambda x: f"{float(x):.2f}")

    valid = betas[betas["beta"].notna() & betas["r2"].notna() & (betas["n_observaciones"] >= 3)].copy()
    beta_by_window = valid.groupby("tipo_ventana")["beta"].median().reindex(["mensual", "trimestral", "semestral"]).dropna()
    r2_by_window = valid.groupby("tipo_ventana")["r2"].median().reindex(["mensual", "trimestral", "semestral"]).dropna()
    n_by_window = valid.groupby("tipo_ventana")["n_observaciones"].median().reindex(["mensual", "trimestral", "semestral"]).dropna()
    valid_pct = resumen_ventana.set_index("ventana")["% valido"].to_dict()
    promo_share = master["promocion"].mean() * 100
    negative_share = (valid["beta"] < 0).mean() * 100 if len(valid) else 0
    insights = [
        f"En Papel hay {summary['skus']} SKUs y {summary['filas_master']:,} observaciones SKU-FECHA; {promo_share:.2f}% de las filas tienen promocion detectada.",
        f"La ventana semestral es la mas estable: tiene mayor porcentaje de betas validas ({valid_pct.get('semestral', 'NA')}) que mensual y trimestral.",
        f"El principal motivo de exclusion es n<3, por lo que muchas ventanas no tienen suficientes observaciones para una regresion confiable.",
        f"Entre las betas validas, {negative_share:.2f}% son negativas; esas son las que siguen la relacion esperada de demanda precio-cantidad.",
        "Las betas mensuales son utiles para detectar cambios bruscos, pero deben interpretarse con mas cuidado por menor numero de observaciones.",
    ]

    heat_beta = valid.pivot_table(index="anio", columns="mes", values="beta", aggfunc="median").reindex(columns=range(1, 13))
    heat_r2 = valid.pivot_table(index="anio", columns="mes", values="r2", aggfunc="median").reindex(columns=range(1, 13))
    heat_n = valid.pivot_table(index="anio", columns="mes", values="n_observaciones", aggfunc="median").reindex(columns=range(1, 13))
    promo_month = (
        master.assign(anio=master["fecha"].dt.year, mes_num=master["fecha"].dt.month)
        .pivot_table(index="anio", columns="mes_num", values="promocion", aggfunc="mean")
        .reindex(columns=range(1, 13))
        * 100
    )
    month_labels = {i: calendar for i, calendar in enumerate(["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"], start=1)}
    for matrix in [heat_beta, heat_r2, heat_n, promo_month]:
        matrix.rename(columns=month_labels, inplace=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(args.output) as pdf:
        add_title_page(pdf, summary)
        add_insights_page(pdf, insights)
        add_table_page(pdf, "Betas validas por tipo de ventana", resumen_ventana, font_size=10)
        add_table_page(pdf, "Razones de exclusion", razones, font_size=10)
        add_bar_page(pdf, "Mediana de beta valida por ventana", beta_by_window.index.tolist(), beta_by_window.tolist(), "Beta mediana")
        add_bar_page(pdf, "Mediana de R2 por ventana", r2_by_window.index.tolist(), r2_by_window.tolist(), "R2 mediana")
        add_bar_page(pdf, "Mediana de observaciones por ventana", n_by_window.index.tolist(), n_by_window.tolist(), "N mediana")
        add_hist_page(pdf, "Distribucion de betas validas", valid["beta"].clip(-20, 20), "Beta (recortada a [-20, 20])")
        add_hist_page(pdf, "Distribucion de R2 en betas validas", valid["r2"], "R2")
        add_heatmap_page(pdf, "Heatmap agregado de beta mediana", heat_beta, "Beta mediana", center_zero=True)
        add_heatmap_page(pdf, "Heatmap agregado de R2 mediana", heat_r2, "R2 mediana", cmap="Blues")
        add_heatmap_page(pdf, "Heatmap agregado de N observaciones", heat_n, "N mediana", cmap="Greens")
        add_heatmap_page(pdf, "Heatmap de porcentaje de filas con promocion", promo_month, "% promocion", cmap="Oranges")
        add_scatter_page(pdf, "Relacion ln(precio) vs ln(qty) por observacion SKU-FECHA", master)
        add_promo_comparison_page(pdf, master)
        add_table_page(pdf, "Top 20 SKUs de Papel con mas betas validas", top_skus, font_size=8)
        add_table_page(pdf, "Cambios importantes de beta por SKU y ventana", cambios_top, font_size=7)

        images = sorted(args.graficas_dir.glob("beta_sku_*.png"))[: args.max_graficas]
        for image in images:
            sku = image.stem.replace("beta_sku_", "")
            add_image_page(pdf, image, f"Beta mensual, trimestral y semestral - SKU {sku}")

    print("Reporte PDF generado")
    print(f"salida: {args.output}")
    print(f"graficas incluidas: {len(sorted(args.graficas_dir.glob('beta_sku_*.png'))[: args.max_graficas])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
