from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


DATE_CONTEXT_PATTERNS = [
    ("dd/mm/yyyy", re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")),
    ("dd-mm-yyyy", re.compile(r"\b\d{1,2}-\d{1,2}-\d{2,4}\b")),
    ("dd.mm.yy", re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b")),
    (
        "dd al dd mes yyyy",
        re.compile(
            r"\b\d{1,2}\s+al\s+\d{1,2}\s+(?:de\s+)?"
            r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+(?:\s+(?:de\s+)?\d{2,4})?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "dd-dd mes yyyy",
        re.compile(
            r"\b\d{1,2}\s*-\s*\d{1,2}\s+"
            r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+(?:\s+(?:de\s+)?\d{2,4})?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "del X al Y",
        re.compile(
            r"\bdel\s+\d{1,2}\s+(?:de\s+)?[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+"
            r"(?:\s+(?:de\s+)?\d{2,4})?\s+al\s+\d{1,2}\s+"
            r"(?:de\s+)?[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+(?:\s+(?:de\s+)?\d{2,4})?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "del X al Y mismo mes",
        re.compile(
            r"\bdel\s+\d{1,2}\s+al\s+\d{1,2}\s+(?:de\s+)?"
            r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+(?:\s+(?:de\s+)?\d{2,4})?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "vigencia",
        re.compile(
            r"\bvigencia\b.{0,80}?(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
            r"\d{1,2}\s+(?:al|a)\s+\d{1,2}\s+(?:de\s+)?[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+"
            r"(?:\s+(?:de\s+)?\d{2,4})?|"
            r"\d{1,2}\s*-\s*\d{1,2}\s+[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+"
            r"(?:\s+(?:de\s+)?\d{2,4})?|"
            r"\d{1,2}\s+(?:de\s+)?[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+(?:\s+(?:de\s+)?\d{2,4})?)",
            re.IGNORECASE,
        ),
    ),
    (
        "valido hasta",
        re.compile(
            r"\bv[aá]lido\s+hasta\b.{0,80}?(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
            r"\d{1,2}\s+(?:de\s+)?[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "hasta el",
        re.compile(
            r"\bhasta\s+el\b.{0,80}?(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
            r"\d{1,2}\s+(?:de\s+)?[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "hasta dia mes",
        re.compile(
            r"\bhasta\s+\d{1,2}\s+(?:de\s+)?[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+"
            r"(?:\s+(?:de\s+)?\d{2,4})?\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass(frozen=True)
class DateHit:
    pattern: str
    match: str
    context: str


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def context_for(text: str, start: int, end: int, width: int = 85) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return normalize_space(text[left:right])


def detect_date_hits(text: str | float | None) -> list[DateHit]:
    if pd.isna(text):
        return []
    source = normalize_space(str(text))
    if not source:
        return []

    hits: list[DateHit] = []
    seen: set[tuple[str, str]] = set()
    for pattern_name, pattern in DATE_CONTEXT_PATTERNS:
        for match in pattern.finditer(source):
            found = normalize_space(match.group(0))
            key = (pattern_name, strip_accents(found))
            if key in seen:
                continue
            seen.add(key)
            hits.append(DateHit(pattern_name, found, context_for(source, match.start(), match.end())))
    return hits


def build_report(master_path: Path, output_path: Path, examples: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    master = pd.read_csv(master_path, dtype=str, encoding="utf-8-sig")
    docs = master[["promo_id", "archivo_origen", "mes_carpeta", "promo_texto"]].drop_duplicates()

    rows: list[dict[str, str]] = []
    for _, row in docs.iterrows():
        hits = detect_date_hits(row.get("promo_texto"))
        for hit in hits:
            rows.append(
                {
                    "promo_id": row.get("promo_id"),
                    "archivo_origen": row.get("archivo_origen"),
                    "mes_carpeta": row.get("mes_carpeta"),
                    "patron_detectado": hit.pattern,
                    "fecha_texto": hit.match,
                    "contexto": hit.context,
                }
            )

    report = pd.DataFrame(
        rows,
        columns=["promo_id", "archivo_origen", "mes_carpeta", "patron_detectado", "fecha_texto", "contexto"],
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False, encoding="utf-8-sig")

    detected_docs = report[["promo_id", "archivo_origen"]].drop_duplicates() if not report.empty else report
    detected_keys = set(map(tuple, detected_docs[["promo_id", "archivo_origen"]].to_numpy())) if not report.empty else set()
    docs = docs.copy()
    docs["fecha_detectable_en_promo_texto"] = [
        "SI" if (row.promo_id, row.archivo_origen) in detected_keys else "NO" for row in docs.itertuples(index=False)
    ]
    examples_df = report.drop_duplicates(["promo_id", "archivo_origen"]).head(examples)
    return docs, examples_df, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Detecta fechas dentro de promo_texto del master de promociones.")
    parser.add_argument("--master", default=Path("output/promociones_master.csv"), type=Path)
    parser.add_argument("--output", default=Path("output/fechas_promo_texto.csv"), type=Path)
    parser.add_argument("--examples", default=20, type=int)
    args = parser.parse_args()

    docs, examples, report = build_report(args.master, args.output, args.examples)
    total_docs = len(docs)
    detected_docs = int((docs["fecha_detectable_en_promo_texto"] == "SI").sum())
    pct_docs = (detected_docs / total_docs * 100) if total_docs else 0

    print("Analisis de fechas en promo_texto")
    print(f"promociones unicas: {total_docs}")
    print(f"promociones con fecha detectable: {detected_docs}")
    print(f"porcentaje con fecha detectable: {pct_docs:.2f}%")
    print(f"reporte CSV: {args.output}")
    print("conteo por patron:")
    if report.empty:
        print("  sin patrones detectados")
    else:
        for pattern_name, count in report["patron_detectado"].value_counts().items():
            print(f"  {pattern_name}: {count}")
    print()
    print(f"Primeros {len(examples)} ejemplos:")
    for i, row in enumerate(examples.itertuples(index=False), start=1):
        print(f"{i}. promo_id={row.promo_id} mes={row.mes_carpeta} patron={row.patron_detectado}")
        print(f"   fecha_texto: {row.fecha_texto}")
        print(f"   contexto: {row.contexto}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
