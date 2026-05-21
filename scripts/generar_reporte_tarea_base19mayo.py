from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


def add_text_page(pdf: PdfPages, title: str, lines: list[str]) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.04, 0.94, title, fontsize=22, fontweight="bold", va="top")
    ax.text(0.06, 0.84, "\n\n".join(lines), fontsize=12.5, va="top")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_table_page(pdf: PdfPages, title: str, df: pd.DataFrame, font_size: int = 9) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.03, 0.96, title, fontsize=18, fontweight="bold", va="top")
    table = ax.table(cellText=df.astype(str).values, colLabels=df.columns, cellLoc="left", colLoc="left", bbox=[0.03, 0.08, 0.94, 0.82])
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    for (row, _col), cell in table.get_celld().items():
        cell.set_edgecolor("#d1d5db")
        if row == 0:
            cell.set_facecolor("#1f2937")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor("#ffffff" if row % 2 else "#f3f4f6")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_bar_page(pdf: PdfPages, title: str, df: pd.DataFrame, x: str, y: str, ylabel: str, color: str = "#2563eb") -> None:
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.bar(df[x].astype(str), pd.to_numeric(df[y], errors="coerce"), color=color)
    ax.set_title(title, fontsize=18, fontweight="bold", loc="left")
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reporte final de tarea con Modelo 1 y Modelo 2.")
    parser.add_argument("--output-dir", default=Path("output/base19mayo"), type=Path)
    parser.add_argument("--output", default=Path("output/base19mayo/reporte_tarea_modelos_base19mayo.pdf"), type=Path)
    args = parser.parse_args()

    diagnostic = pd.read_csv(args.output_dir / "diagnostico_betas.csv", encoding="utf-8-sig")
    model2_summary = pd.read_csv(args.output_dir / "modelo2_multivariable_resumen.csv", encoding="utf-8-sig")
    model2_coef = pd.read_csv(args.output_dir / "modelo2_multivariable_coeficientes.csv", encoding="utf-8-sig")
    model2_dept = pd.read_csv(args.output_dir / "modelo2_multivariable_por_departamento.csv", encoding="utf-8-sig")
    model2_sku = pd.read_csv(args.output_dir / "modelo2_multivariable_sku.csv", encoding="utf-8-sig")

    model1_window = diagnostic[diagnostic["seccion"] == "resumen_por_ventana"].copy()
    model1_window = model1_window.rename(columns={"metric": "ventana", "valor": "betas_validas", "porcentaje": "% valido", "detalle": "detalle"})
    model1_window = model1_window[["ventana", "betas_validas", "% valido", "detalle"]]
    model1_window["% valido"] = model1_window["% valido"].map(lambda x: f"{float(x):.2f}%")

    model1_reasons = diagnostic[diagnostic["seccion"] == "razones_exclusion"].copy()
    model1_reasons = model1_reasons.rename(columns={"metric": "razon", "valor": "ventanas", "porcentaje": "%"})
    model1_reasons = model1_reasons[["razon", "ventanas", "%"]]
    model1_reasons["%"] = model1_reasons["%"].map(lambda x: f"{float(x):.2f}%")

    top_coef = model2_coef.head(25).copy()
    top_coef["coeficiente"] = top_coef["coeficiente"].map(lambda x: f"{float(x):.4f}")
    top_coef = top_coef[["variable", "coeficiente"]]

    model2_dept_fmt = model2_dept.copy()
    for col in ["r2_modelo", "beta_precio"]:
        model2_dept_fmt[col] = model2_dept_fmt[col].map(lambda x: f"{float(x):.4f}")

    sku_status = model2_sku["estatus"].value_counts().reset_index()
    sku_status.columns = ["estatus", "SKUs"]
    sku_status["%"] = sku_status["SKUs"] / sku_status["SKUs"].sum() * 100
    sku_status["%"] = sku_status["%"].map(lambda x: f"{float(x):.2f}%")

    r2 = float(model2_summary.loc[model2_summary["metric"] == "r2_modelo", "valor"].iloc[0])
    beta_global = float(model2_summary.loc[model2_summary["metric"] == "elasticidad_precio_ln_precio", "valor"].iloc[0])
    n_obs = int(float(model2_summary.loc[model2_summary["metric"] == "n_observaciones", "valor"].iloc[0]))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(args.output) as pdf:
        add_text_page(
            pdf,
            "Entrega Elasticidad - Base OfficeMax 19 mayo",
            [
                "Objetivo: estimar elasticidad precio-cantidad con modelo log-log y generar una lectura dinamica por SKU usando ventanas moviles.",
                "Base usada: Base_OfficeMax19mayo.csv. La base tiene 26,980 registros, 1,750 SKUs, 85 tiendas y ventas entre 2024-01 y 2026-04.",
                "Nota de categoria: la nueva base no contiene dept_nm = PAPEL. Por eso el flujo se dejo parametrizable por departamento y tambien se corrio para todos los departamentos disponibles.",
            ],
        )
        add_text_page(
            pdf,
            "Modelo 1: log-log por ventanas moviles",
            [
                "Modelo: ln(qty) ~ ln(precio).",
                "Granularidad usada: SKU x tienda x mes. Esto permite que una ventana mensual tenga varias observaciones por tienda.",
                "Ventanas: mensual = mes 1, 2, 3; trimestral = 1-3, 2-4, 3-5; semestral = 1-6, 2-7, 3-8.",
                "Para cada SKU y ventana se guarda beta, R2, n_observaciones y estatus de estimacion.",
            ],
        )
        add_table_page(pdf, "Modelo 1 - Betas validas por ventana", model1_window)
        add_table_page(pdf, "Modelo 1 - Razones de exclusion", model1_reasons)
        add_bar_page(pdf, "Modelo 1 - Betas validas por ventana", model1_window.assign(betas_validas=pd.to_numeric(model1_window["betas_validas"])), "ventana", "betas_validas", "Betas validas")
        add_text_page(
            pdf,
            "Modelo 2: log-log multivariable",
            [
                "Modelo: ln(qty) ~ ln(precio) + margen + ln(costo_unitario) + fechas_venta + mes + anio + tienda + departamento + subdepartamento + tipo_marca.",
                "Este modelo no busca una beta por ventana, sino entender la explicabilidad general de variables adicionales sobre cantidad vendida.",
                f"Resultado global: R2 = {r2:.4f}; beta precio global = {beta_global:.4f}; observaciones usadas = {n_obs:,}.",
                "Se excluyo net_sale como variable explicativa porque contiene precio x cantidad y generaria fuga matematica.",
            ],
        )
        add_table_page(pdf, "Modelo 2 - Coeficientes mas relevantes", top_coef, font_size=8)
        add_table_page(pdf, "Modelo 2 - Resultado por departamento", model2_dept_fmt, font_size=8)
        add_table_page(pdf, "Modelo 2 - Viabilidad granular por SKU", sku_status, font_size=10)
        add_text_page(
            pdf,
            "Interpretacion ejecutiva",
            [
                "El Modelo 1 es el mas adecuado para elasticidad dinamica por SKU, porque estima beta en ventanas moviles y muestra cambios temporales.",
                "El Modelo 2 ayuda a explicar cantidad vendida de forma general. En esta base, las variables de calendario, tienda, subdepartamento, margen y costo agregan explicabilidad.",
                "La beta precio global del Modelo 2 es cercana a cero, lo que sugiere que al controlar por tienda, subdepartamento y estacionalidad, la variacion de precio promedio no explica mucho la cantidad total.",
                "A nivel SKU, el Modelo 2 no es tan viable porque muchos SKUs tienen precio constante; por eso para granularidad SKU conviene reportar Modelo 1.",
            ],
        )

    print("Reporte de tarea generado")
    print(f"salida: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
