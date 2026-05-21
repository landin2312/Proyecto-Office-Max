from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description="Filtra MASTER_FINAL y betas dinamicas al departamento PAPEL.")
    parser.add_argument("--master", default=Path("output/MASTER_FINAL_SKU_FECHA.csv"), type=Path)
    parser.add_argument("--betas", default=Path("output/elasticidad_dinamica_betas_sku_fecha.csv"), type=Path)
    parser.add_argument("--dept", default="PAPEL")
    parser.add_argument("--output-master", default=Path("output/MASTER_FINAL_SKU_FECHA_PAPEL.csv"), type=Path)
    parser.add_argument("--output-betas", default=Path("output/elasticidad_dinamica_betas_papel.csv"), type=Path)
    args = parser.parse_args()

    master = pd.read_csv(args.master, dtype={"prod_nbr": str}, encoding="utf-8-sig")
    betas = pd.read_csv(args.betas, dtype={"SKU": str}, encoding="utf-8-sig")

    dept = args.dept.strip().upper()
    paper_master = master[master["dept_nm"].fillna("").str.strip().str.upper() == dept].copy()
    paper_skus = set(paper_master["prod_nbr"].dropna().astype(str).unique())
    paper_betas = betas[betas["SKU"].astype(str).isin(paper_skus)].copy()

    args.output_master.parent.mkdir(parents=True, exist_ok=True)
    paper_master.to_csv(args.output_master, index=False, encoding="utf-8-sig")
    paper_betas.to_csv(args.output_betas, index=False, encoding="utf-8-sig")

    print("Filtro departamento")
    print(f"departamento: {dept}")
    print(f"filas master: {len(paper_master)}")
    print(f"SKUs master: {paper_master['prod_nbr'].nunique()}")
    print(f"fechas master: {paper_master['fecha'].nunique()}")
    print(f"filas con promocion: {int(pd.to_numeric(paper_master['promocion'], errors='coerce').fillna(0).sum())}")
    print(f"filas betas: {len(paper_betas)}")
    print(f"betas calculables: {int(pd.to_numeric(paper_betas['beta'], errors='coerce').notna().sum())}")
    print(f"salida master: {args.output_master}")
    print(f"salida betas: {args.output_betas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
