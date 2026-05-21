from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


def clean_name(value: object, max_len: int = 38) -> str:
    text = "" if pd.isna(value) else str(value)
    return text[:max_len]


def load(master_path: Path, betas_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    master = pd.read_csv(master_path, dtype={"prod_nbr": str, "store_nbr": str}, encoding="utf-8-sig")
    betas = pd.read_csv(betas_path, dtype={"SKU": str}, encoding="utf-8-sig")
    for col in ["qty", "precio", "net_sale", "margen"]:
        master[col] = pd.to_numeric(master[col], errors="coerce")
    master["fecha_mes"] = pd.to_datetime(master["fecha_mes"], errors="coerce")
    for col in ["beta", "r2", "n_observaciones"]:
        betas[col] = pd.to_numeric(betas[col], errors="coerce")
    betas["periodo_inicio"] = pd.to_datetime(betas["periodo_inicio"], errors="coerce")
    betas["periodo_fin"] = pd.to_datetime(betas["periodo_fin"], errors="coerce")
    betas["periodo"] = betas["periodo_inicio"].dt.strftime("%Y-%m") + " a " + betas["periodo_fin"].dt.strftime("%Y-%m")
    product = master[["prod_nbr", "dept_nm", "subdept_nm", "class_nm", "marca"]].drop_duplicates("prod_nbr").rename(columns={"prod_nbr": "SKU"})
    return master, betas, product


def valid_betas(betas: pd.DataFrame, window: str = "trimestral") -> pd.DataFrame:
    out = betas[(betas["tipo_ventana"] == window) & (betas["estatus_beta"] == "valida")].copy()
    return out.sort_values(["SKU", "periodo_inicio"])


def cover(pdf: PdfPages, master: pd.DataFrame, tri: pd.DataFrame, label: str) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    elastic = int((tri["beta"] < -1).sum())
    anomalous = int((tri["beta"] >= 0).sum())
    robust = int((tri["r2"] >= 0.2).sum())
    ax.text(0.5, 0.91, "Analisis de Elasticidad de Precios", ha="center", fontsize=25, fontweight="bold")
    ax.text(0.5, 0.85, f"Base OfficeMax 19 mayo | {label} | 2024-2026", ha="center", fontsize=14)
    ax.text(0.5, 0.77, "ln(unidades) = alpha + beta · ln(precio)", ha="center", fontsize=18)
    metrics = [
        (master["prod_nbr"].nunique(), "SKUs"),
        (master["store_nbr"].nunique(), "Tiendas"),
        (len(tri), "Estimaciones trim."),
        (robust, "R2 >= 0.20"),
        (elastic, "Elasticas beta<-1"),
        (anomalous, "Anomalas beta>=0"),
    ]
    xs = np.linspace(0.13, 0.87, 3)
    ys = [0.60, 0.42]
    for i, (value, name) in enumerate(metrics):
        ax.text(xs[i % 3], ys[i // 3], f"{value:,}", ha="center", fontsize=28, fontweight="bold")
        ax.text(xs[i % 3], ys[i // 3] - 0.055, name, ha="center", fontsize=12, color="#4b5563")
    notes = [
        "Agregacion: SKU x tienda x mes",
        "Ventanas forward: mensual 1, trimestral 1-3, semestral 1-6",
        "Beta < -1: elastico | -1 < beta < 0: inelastico | beta >= 0: anomalo",
        "Esta estructura permite conectar una base nueva al mismo modelo si respeta columnas equivalentes.",
    ]
    ax.text(0.14, 0.25, "\n".join(notes), fontsize=13, va="top")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def insights(pdf: PdfPages, master: pd.DataFrame, tri: pd.DataFrame) -> None:
    median_beta = tri["beta"].median()
    median_r2 = tri["r2"].median()
    elastic_pct = (tri["beta"] < -1).mean() * 100 if len(tri) else 0
    anomalous_pct = (tri["beta"] >= 0).mean() * 100 if len(tri) else 0
    dept_mix = master["dept_nm"].value_counts(normalize=True).head(4).mul(100)
    dept_text = "; ".join(f"{idx}: {val:.1f}%" for idx, val in dept_mix.items())
    lines = [
        f"La beta mediana trimestral es {median_beta:.2f}; es la lectura central de sensibilidad precio-cantidad.",
        f"{elastic_pct:.2f}% de las betas trimestrales validas son elasticas (beta < -1).",
        f"{anomalous_pct:.2f}% son positivas/anomalas; conviene revisarlas por estacionalidad, inventario o baja variacion de precio.",
        f"La mediana de R2 es {median_r2:.2f}; por eso se reporta beta junto con R2 y n_observaciones.",
        f"Mezcla de departamentos en la base: {dept_text}.",
    ]
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.04, 0.94, "Insights principales", fontsize=22, fontweight="bold", va="top")
    ax.text(0.06, 0.83, "\n\n".join(f"{i+1}. {line}" for i, line in enumerate(lines)), fontsize=13, va="top")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def heatmap(pdf: PdfPages, tri: pd.DataFrame, product: pd.DataFrame, value: str, title: str, cmap: str, vmin=None, vmax=None) -> None:
    top = tri.groupby("SKU")["beta"].count().sort_values(ascending=False).head(24).index
    plot = tri[tri["SKU"].isin(top)].merge(product, on="SKU", how="left")
    plot["label"] = plot["SKU"] + " | " + plot["subdept_nm"].fillna("")
    matrix = plot.pivot_table(index="label", columns="periodo", values=value, aggfunc="mean")
    if value == "beta":
        matrix_plot = matrix.clip(-10, 10)
        vmin, vmax = -10, 10
    else:
        matrix_plot = matrix
    fig, ax = plt.subplots(figsize=(14, 9))
    im = ax.imshow(matrix_plot, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title, fontsize=18, fontweight="bold", loc="left")
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels([clean_name(x, 48) for x in matrix.index], fontsize=8)
    fig.colorbar(im, ax=ax, label=value)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def seasonality(pdf: PdfPages, tri: pd.DataFrame) -> None:
    agg = tri.groupby("periodo").agg(beta_promedio=("beta", "mean"), beta_mediana=("beta", "median"), pct_elastico=("beta", lambda s: (s < -1).mean() * 100), skus=("SKU", "nunique")).reset_index()
    order = tri.drop_duplicates("periodo").sort_values("periodo_inicio")["periodo"].tolist()
    agg["periodo"] = pd.Categorical(agg["periodo"], categories=order, ordered=True)
    agg = agg.sort_values("periodo")
    x = np.arange(len(agg))
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
    axes[0].plot(x, agg["beta_promedio"], marker="o", label="Promedio")
    axes[0].plot(x, agg["beta_mediana"], marker="s", label="Mediana")
    axes[0].axhline(-1, color="#dc2626", linestyle="--")
    axes[0].axhline(0, color="#111827", linewidth=1)
    axes[0].set_title("Estacionalidad trimestral", fontsize=18, fontweight="bold", loc="left")
    axes[0].set_ylabel("Beta")
    axes[0].legend()
    axes[0].grid(alpha=0.25)
    axes[1].bar(x, agg["pct_elastico"], color="#d97706", label="% elasticos")
    axes[1].plot(x, agg["skus"], color="#111827", marker="o", label="# SKUs")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(agg["periodo"], rotation=60, ha="right", fontsize=8)
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.25)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def sku_panels(pdf: PdfPages, tri: pd.DataFrame, product: pd.DataFrame, top_n: int = 20) -> None:
    skus = tri.groupby("SKU")["beta"].count().sort_values(ascending=False).head(top_n).index.tolist()
    plot = tri[tri["SKU"].isin(skus)].merge(product, on="SKU", how="left")
    pages = math.ceil(len(skus) / 4)
    for page in range(pages):
        fig, axes = plt.subplots(2, 2, figsize=(14, 9))
        axes = axes.ravel()
        for idx, sku in enumerate(skus[page * 4 : (page + 1) * 4]):
            ax = axes[idx]
            g = plot[plot["SKU"] == sku].sort_values("periodo_inicio")
            x = np.arange(len(g))
            colors = ["#dc2626" if b < -1 else "#059669" if b < 0 else "#2563eb" for b in g["beta"]]
            ax.plot(x, g["beta"], color="#111827", linewidth=1.3, alpha=0.6)
            ax.scatter(x, g["beta"], c=colors, s=32)
            ax.axhline(-1, color="#dc2626", linestyle="--", linewidth=1)
            ax.axhline(0, color="#111827", linewidth=1)
            ax.set_title(f"SKU {sku} | {clean_name(g['subdept_nm'].iloc[0], 28)}", fontsize=10)
            ax.set_ylabel("Beta")
            ax.grid(alpha=0.25)
        for ax in axes[len(skus[page * 4 : (page + 1) * 4]) :]:
            ax.axis("off")
        fig.suptitle(f"Evolucion de beta por SKU - trimestral [pag. {page+1}/{pages}]", fontsize=17, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        pdf.savefig(fig)
        plt.close(fig)


def top_pages(pdf: PdfPages, tri: pd.DataFrame, product: pd.DataFrame) -> None:
    avg = tri.groupby("SKU").agg(beta_promedio=("beta", "mean"), bloques=("beta", "count"), r2_mediana=("r2", "median")).reset_index().merge(product, on="SKU", how="left")
    for title, table, color in [
        ("Top 15 SKUs mas elasticos", avg[avg["bloques"] >= 3].sort_values("beta_promedio").head(15), "#dc2626"),
        ("Top 15 SKUs con beta positiva/anomala", avg[avg["bloques"] >= 3].sort_values("beta_promedio", ascending=False).head(15), "#2563eb"),
    ]:
        fig, ax = plt.subplots(figsize=(11, 8.5))
        labels = [f"{row.SKU} | {clean_name(row.subdept_nm, 28)}" for row in table.itertuples()]
        ax.barh(labels, table["beta_promedio"], color=color)
        ax.axvline(-1 if color == "#dc2626" else 0, color="#111827", linestyle="--")
        ax.set_title(title, fontsize=18, fontweight="bold", loc="left")
        ax.set_xlabel("Beta promedio trimestral")
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.25)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)


def scatter_page(pdf: PdfPages, master: pd.DataFrame) -> None:
    plot = master[(master["precio"] > 0) & (master["qty"] > 0)].copy()
    plot["ln_precio"] = np.log(plot["precio"])
    plot["ln_qty"] = np.log(plot["qty"])
    sample = plot.sample(min(len(plot), 12000), random_state=7)
    fig, ax = plt.subplots(figsize=(11, 8.5))
    for dept, g in sample.groupby("dept_nm"):
        ax.scatter(g["ln_precio"], g["ln_qty"], s=12, alpha=0.35, label=dept)
    ax.set_title("Relacion ln(precio) vs ln(qty) por SKU-tienda-mes", fontsize=18, fontweight="bold", loc="left")
    ax.set_xlabel("ln(precio)")
    ax.set_ylabel("ln(qty)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera reporte PDF estilo ejemplo para Base_OfficeMax19mayo.")
    parser.add_argument("--master", default=Path("output/base19mayo/MASTER_SKU_TIENDA_MES.csv"), type=Path)
    parser.add_argument("--betas", default=Path("output/base19mayo/betas_dinamicas.csv"), type=Path)
    parser.add_argument("--label", default="TODOS LOS DEPARTAMENTOS")
    parser.add_argument("--output", default=Path("output/base19mayo/reporte_base19mayo_estilo_ejemplo.pdf"), type=Path)
    args = parser.parse_args()
    master, betas, product = load(args.master, args.betas)
    tri = valid_betas(betas, "trimestral")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(args.output) as pdf:
        cover(pdf, master, tri, args.label)
        insights(pdf, master, tri)
        heatmap(pdf, tri, product, "beta", "Mapa de Elasticidad: beta por SKU y trimestre", "RdBu_r")
        heatmap(pdf, tri, product, "r2", "Mapa de Calidad: R2 por SKU y trimestre", "Blues", 0, 1)
        seasonality(pdf, tri)
        sku_panels(pdf, tri, product)
        top_pages(pdf, tri, product)
        scatter_page(pdf, master)
    print("Reporte generado")
    print(f"salida: {args.output}")
    print(f"estimaciones trimestrales validas: {len(tri)}")
    print(f"SKUs con beta trimestral: {tri['SKU'].nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
