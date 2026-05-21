from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


WINDOW = "trimestral"
MAX_ABS_BETA_HEATMAP = 10


def clean_name(value: object, max_len: int = 34) -> str:
    text = "" if pd.isna(value) else str(value)
    return text[:max_len]


def period_label(start: pd.Timestamp, end: pd.Timestamp) -> str:
    return f"{start:%Y-%m} a {end:%Y-%m}"


def classify_beta(beta: float) -> str:
    if pd.isna(beta):
        return "Sin dato"
    if beta < -1:
        return "Elastico"
    if beta < 0:
        return "Inelastico"
    return "Anomalo"


def load_data(betas_path: Path, master_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    betas = pd.read_csv(betas_path, dtype={"SKU": str}, encoding="utf-8-sig")
    master = pd.read_csv(master_path, dtype={"prod_nbr": str}, encoding="utf-8-sig")

    for col in ["beta", "r2", "n_observaciones"]:
        betas[col] = pd.to_numeric(betas[col], errors="coerce")
    betas["periodo_inicio"] = pd.to_datetime(betas["periodo_inicio"], errors="coerce")
    betas["periodo_fin"] = pd.to_datetime(betas["periodo_fin"], errors="coerce")
    betas["periodo"] = [period_label(s, e) for s, e in zip(betas["periodo_inicio"], betas["periodo_fin"])]

    for col in ["precio", "qty", "promocion", "descuento"]:
        master[col] = pd.to_numeric(master[col], errors="coerce")
    master["fecha"] = pd.to_datetime(master["fecha"], errors="coerce")

    product = (
        master[["prod_nbr", "prod_nm", "subdept_nm", "class_nm"]]
        .drop_duplicates("prod_nbr")
        .rename(columns={"prod_nbr": "SKU"})
    )
    return betas, master, product


def usable_trimestral(betas: pd.DataFrame) -> pd.DataFrame:
    tri = betas[betas["tipo_ventana"] == WINDOW].copy()
    tri = tri[tri["beta"].notna() & tri["r2"].notna() & (tri["n_observaciones"] >= 3)]
    return tri.sort_values(["SKU", "periodo_inicio"])


def cover_page(pdf: PdfPages, tri: pd.DataFrame, master: pd.DataFrame, product: pd.DataFrame) -> None:
    total_skus = product["SKU"].nunique()
    skus_with_beta = tri["SKU"].nunique()
    estimaciones = len(tri)
    robust = tri[tri["r2"] >= 0.2]
    elastic = tri[tri["beta"] < -1]
    anomalous = tri[tri["beta"] >= 0]

    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.5, 0.92, "Analisis de Elasticidad de Precios", ha="center", fontsize=25, fontweight="bold")
    ax.text(0.5, 0.86, "Departamento: PAPEL | OfficeMax | 2024-2026", ha="center", fontsize=14)
    ax.text(0.5, 0.77, "ln(unidades) = alpha + beta · ln(precio)", ha="center", fontsize=18)

    metrics = [
        (total_skus, "SKUs Papel"),
        (skus_with_beta, "SKUs con beta trim."),
        (estimaciones, "Estimaciones trim."),
        (len(robust), "R2 >= 0.20"),
        (len(elastic), "Elasticas beta<-1"),
        (len(anomalous), "Anomalas beta>=0"),
    ]
    x_positions = np.linspace(0.12, 0.88, 3)
    y_positions = [0.61, 0.43]
    for idx, (value, label) in enumerate(metrics):
        x = x_positions[idx % 3]
        y = y_positions[idx // 3]
        ax.text(x, y, f"{value:,}", ha="center", fontsize=28, fontweight="bold", color="#1f2937")
        ax.text(x, y - 0.055, label, ha="center", fontsize=12, color="#4b5563")

    legend = [
        "Elastico: beta < -1",
        "Inelastico: -1 < beta < 0",
        "Anomalo: beta >= 0",
        "Ventanas trimestrales forward: 1-3, 2-4, 3-5, 4-6",
        "Precio usado: net_sale / qty | Granularidad base: SKU-FECHA",
    ]
    ax.text(0.16, 0.25, "\n".join(legend), fontsize=13, va="top")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def beta_heatmap_page(pdf: PdfPages, tri: pd.DataFrame, product: pd.DataFrame, top_n: int = 22) -> None:
    sku_counts = tri.groupby("SKU")["beta"].count().sort_values(ascending=False).head(top_n).index
    plot = tri[tri["SKU"].isin(sku_counts)].merge(product, on="SKU", how="left")
    matrix = plot.pivot_table(index="prod_nm", columns="periodo", values="beta", aggfunc="mean")
    matrix = matrix.loc[[name for name in plot.drop_duplicates("prod_nm")["prod_nm"] if name in matrix.index]]
    clipped = matrix.clip(-MAX_ABS_BETA_HEATMAP, MAX_ABS_BETA_HEATMAP)

    fig, ax = plt.subplots(figsize=(14, 9))
    image = ax.imshow(clipped, aspect="auto", cmap="RdBu_r", vmin=-MAX_ABS_BETA_HEATMAP, vmax=MAX_ABS_BETA_HEATMAP)
    ax.set_title("Mapa de Elasticidad: Beta por SKU y Trimestre", fontsize=18, fontweight="bold", loc="left")
    ax.set_xlabel("Trimestre")
    ax.set_ylabel("SKU")
    ax.set_xticks(range(len(clipped.columns)))
    ax.set_xticklabels(clipped.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(clipped.index)))
    ax.set_yticklabels([clean_name(x, 42) for x in clipped.index], fontsize=8)
    for i in range(clipped.shape[0]):
        for j in range(clipped.shape[1]):
            value = matrix.iloc[i, j]
            if pd.notna(value):
                ax.text(j, i, f"{value:.1f}", ha="center", va="center", fontsize=6)
    fig.colorbar(image, ax=ax, label="Beta (recortada visualmente a +/-10)")
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def r2_heatmap_page(pdf: PdfPages, tri: pd.DataFrame, product: pd.DataFrame, top_n: int = 22) -> None:
    sku_counts = tri.groupby("SKU")["beta"].count().sort_values(ascending=False).head(top_n).index
    plot = tri[tri["SKU"].isin(sku_counts)].merge(product, on="SKU", how="left")
    matrix = plot.pivot_table(index="prod_nm", columns="periodo", values="r2", aggfunc="mean")
    matrix = matrix.loc[[name for name in plot.drop_duplicates("prod_nm")["prod_nm"] if name in matrix.index]]

    fig, ax = plt.subplots(figsize=(14, 9))
    image = ax.imshow(matrix, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_title("Mapa de Calidad: R2 por SKU y Trimestre", fontsize=18, fontweight="bold", loc="left")
    ax.set_xlabel("Trimestre")
    ax.set_ylabel("SKU")
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels([clean_name(x, 42) for x in matrix.index], fontsize=8)
    fig.colorbar(image, ax=ax, label="R2")
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def seasonality_page(pdf: PdfPages, tri: pd.DataFrame) -> None:
    grouped = (
        tri.groupby("periodo")
        .agg(
            beta_promedio=("beta", "mean"),
            beta_mediana=("beta", "median"),
            pct_elastico=("beta", lambda s: (s < -1).mean() * 100),
            skus=("SKU", "nunique"),
        )
        .reset_index()
    )
    order = tri.drop_duplicates("periodo").sort_values("periodo_inicio")["periodo"].tolist()
    grouped["periodo"] = pd.Categorical(grouped["periodo"], categories=order, ordered=True)
    grouped = grouped.sort_values("periodo")

    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    x = np.arange(len(grouped))
    axes[0].plot(x, grouped["beta_promedio"], marker="o", label="Beta promedio", color="#2563eb")
    axes[0].plot(x, grouped["beta_mediana"], marker="s", label="Beta mediana", color="#059669")
    axes[0].axhline(-1, color="#dc2626", linestyle="--", label="Umbral elastico")
    axes[0].axhline(0, color="#111827", linewidth=1)
    axes[0].set_ylabel("Beta")
    axes[0].set_title("Estacionalidad Trimestral - Departamento PAPEL", fontsize=18, fontweight="bold", loc="left")
    axes[0].legend()
    axes[0].grid(alpha=0.25)

    axes[1].bar(x, grouped["pct_elastico"], color="#d97706", label="% SKUs elasticos")
    axes[1].plot(x, grouped["skus"], color="#111827", marker="o", label="# SKUs con beta")
    axes[1].set_ylabel("% elasticos / # SKUs")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(grouped["periodo"], rotation=60, ha="right", fontsize=8)
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.25)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def sku_evolution_pages(pdf: PdfPages, tri: pd.DataFrame, product: pd.DataFrame, top_n: int = 20) -> None:
    sku_order = tri.groupby("SKU")["beta"].count().sort_values(ascending=False).head(top_n).index.tolist()
    plot = tri[tri["SKU"].isin(sku_order)].merge(product, on="SKU", how="left")
    pages = math.ceil(len(sku_order) / 4)
    for page in range(pages):
        fig, axes = plt.subplots(2, 2, figsize=(14, 9))
        axes = axes.ravel()
        for ax_idx, sku in enumerate(sku_order[page * 4 : (page + 1) * 4]):
            ax = axes[ax_idx]
            g = plot[plot["SKU"] == sku].sort_values("periodo_inicio")
            x = np.arange(len(g))
            colors = ["#dc2626" if b < -1 else "#059669" if b < 0 else "#2563eb" for b in g["beta"]]
            ax.plot(x, g["beta"], color="#111827", linewidth=1.5, alpha=0.55)
            ax.scatter(x, g["beta"], c=colors, s=34)
            ax.axhline(-1, color="#dc2626", linestyle="--", linewidth=1)
            ax.axhline(0, color="#111827", linewidth=1)
            name = clean_name(g["prod_nm"].iloc[0], 36)
            subdept = clean_name(g["subdept_nm"].iloc[0], 28)
            ax.set_title(f"{name}\n{subdept} | SKU {sku}", fontsize=10)
            ax.set_ylabel("Beta")
            ax.set_xlabel("Bloque trimestral")
            ax.grid(alpha=0.25)
            if len(g) <= 8:
                ax.set_xticks(x)
                ax.set_xticklabels(g["periodo"].str.slice(0, 7), rotation=45, ha="right", fontsize=7)
        for ax in axes[len(sku_order[page * 4 : (page + 1) * 4]) :]:
            ax.axis("off")
        fig.suptitle(
            f"Evolucion de Beta por SKU - Ventanas Trimestrales [pag. {page + 1}/{pages}]",
            fontsize=17,
            fontweight="bold",
        )
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        pdf.savefig(fig)
        plt.close(fig)


def top_elastic_page(pdf: PdfPages, tri: pd.DataFrame, product: pd.DataFrame) -> None:
    avg = (
        tri.groupby("SKU")
        .agg(beta_promedio=("beta", "mean"), beta_mediana=("beta", "median"), bloques=("beta", "count"))
        .reset_index()
        .merge(product, on="SKU", how="left")
    )
    top = avg[avg["bloques"] >= 3].sort_values("beta_promedio").head(15)

    fig, ax = plt.subplots(figsize=(11, 8.5))
    labels = [clean_name(x, 42) for x in top["prod_nm"]]
    ax.barh(labels, top["beta_promedio"], color="#dc2626")
    ax.axvline(-1, color="#111827", linestyle="--", label="Umbral elastico beta=-1")
    ax.set_title("Top 15 SKUs con Mayor Elasticidad Promedio - Trimestral", fontsize=18, fontweight="bold", loc="left")
    ax.set_xlabel("Beta promedio trimestral")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25)
    ax.legend()
    for i, value in enumerate(top["beta_promedio"]):
        ax.text(value, i, f" {value:.2f}", va="center", fontsize=8)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def anomaly_page(pdf: PdfPages, tri: pd.DataFrame, product: pd.DataFrame) -> None:
    avg = (
        tri.groupby("SKU")
        .agg(beta_promedio=("beta", "mean"), bloques=("beta", "count"), r2_mediana=("r2", "median"))
        .reset_index()
        .merge(product, on="SKU", how="left")
    )
    top = avg[avg["bloques"] >= 3].sort_values("beta_promedio", ascending=False).head(15)

    fig, ax = plt.subplots(figsize=(11, 8.5))
    labels = [clean_name(x, 42) for x in top["prod_nm"]]
    ax.barh(labels, top["beta_promedio"], color="#2563eb")
    ax.axvline(0, color="#111827", linestyle="--", label="Beta positiva")
    ax.set_title("Top 15 SKUs con Beta Positiva Promedio - Posibles Anomalias", fontsize=18, fontweight="bold", loc="left")
    ax.set_xlabel("Beta promedio trimestral")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def price_quantity_page(pdf: PdfPages, master: pd.DataFrame) -> None:
    plot = master[(master["precio"] > 0) & (master["qty"] > 0)].copy()
    plot["ln_precio"] = np.log(plot["precio"])
    plot["ln_qty"] = np.log(plot["qty"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))
    axes[0].scatter(plot["ln_precio"], plot["ln_qty"], c=np.where(plot["promocion"] > 0, "#dc2626", "#2563eb"), alpha=0.35, s=18)
    axes[0].set_title("Relacion ln(precio) vs ln(qty)")
    axes[0].set_xlabel("ln(precio)")
    axes[0].set_ylabel("ln(qty)")
    axes[0].grid(alpha=0.25)

    promo = (
        master.assign(tipo=np.where(master["promocion"] > 0, "Con promocion", "Sin promocion"))
        .groupby("tipo")
        .agg(precio=("precio", "mean"), qty=("qty", "mean"))
        .reset_index()
    )
    x = np.arange(len(promo))
    axes[1].bar(x - 0.18, promo["precio"], width=0.36, label="Precio promedio", color="#2563eb")
    axes[1].bar(x + 0.18, promo["qty"], width=0.36, label="Qty promedio", color="#d97706")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(promo["tipo"])
    axes[1].set_title("Promocion vs no promocion")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle("Evidencia precio-cantidad para PAPEL", fontsize=18, fontweight="bold")
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def insights_page(pdf: PdfPages, tri: pd.DataFrame, master: pd.DataFrame) -> None:
    elastic_pct = (tri["beta"] < -1).mean() * 100
    anomaly_pct = (tri["beta"] >= 0).mean() * 100
    median_beta = tri["beta"].median()
    median_r2 = tri["r2"].median()
    promo_pct = master["promocion"].mean() * 100
    insights = [
        f"La beta mediana trimestral de Papel es {median_beta:.2f}; esto resume el comportamiento central de las ventanas con datos validos.",
        f"{elastic_pct:.2f}% de las estimaciones trimestrales validas son elasticas (beta < -1).",
        f"{anomaly_pct:.2f}% son positivas/anomalas; estas deben revisarse por estacionalidad, promociones no capturadas, inventario o pocos datos.",
        f"La mediana de R2 es {median_r2:.2f}; por eso conviene presentar beta junto con R2 y n_observaciones.",
        f"Solo {promo_pct:.2f}% de las filas SKU-FECHA de Papel tienen promocion detectada, lo cual limita el analisis promocional puro.",
    ]

    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.04, 0.94, "Insights principales", fontsize=22, fontweight="bold", va="top")
    ax.text(0.06, 0.83, "\n\n".join(f"{i + 1}. {text}" for i, text in enumerate(insights)), fontsize=13, va="top")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reporte estilo ejemplo mejorado para elasticidad de Papel.")
    parser.add_argument("--betas", default=Path("output/elasticidad_dinamica_betas_papel.csv"), type=Path)
    parser.add_argument("--master", default=Path("output/MASTER_FINAL_SKU_FECHA_PAPEL.csv"), type=Path)
    parser.add_argument("--output", default=Path("output/reporte_elasticidad_papel_estilo_ejemplo.pdf"), type=Path)
    args = parser.parse_args()

    betas, master, product = load_data(args.betas, args.master)
    tri = usable_trimestral(betas)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(args.output) as pdf:
        cover_page(pdf, tri, master, product)
        insights_page(pdf, tri, master)
        beta_heatmap_page(pdf, tri, product)
        r2_heatmap_page(pdf, tri, product)
        seasonality_page(pdf, tri)
        sku_evolution_pages(pdf, tri, product)
        top_elastic_page(pdf, tri, product)
        anomaly_page(pdf, tri, product)
        price_quantity_page(pdf, master)

    print("Reporte estilo ejemplo generado")
    print(f"salida: {args.output}")
    print(f"estimaciones trimestrales usadas: {len(tri)}")
    print(f"SKUs con beta trimestral: {tri['SKU'].nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
