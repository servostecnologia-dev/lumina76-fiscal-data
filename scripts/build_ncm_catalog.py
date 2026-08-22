#!/usr/bin/env python3
"""Gera o catálogo NCM normalizado do Lumina76 Fiscal Data.

Fonte oficial: Receita Federal / Sistema Classif / Portal Único Siscomex.
O endpoint oficial retorna apenas a NCM vigente. Por isso, este repositório
preserva snapshots históricos a cada atualização.
"""
from __future__ import annotations

import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NCM_DIR = ROOT / "ncm"
META_DIR = ROOT / "metadata"

NCM_URL = "https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json"
SOURCE_ID = "RFB_CLASSIF_NCM_JSON"


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Lumina76-Fiscal-Data/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


def clean_code(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "codigo", "codigo_formatado", "descricao", "data_inicio", "data_fim",
        "tipo_orgao_ato_ini", "numero_ato_ini", "ano_ato_ini",
        "source_id", "data_ultima_alteracao", "snapshot_gerado_em",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    payload = fetch_json(NCM_URL)
    data_ultima = payload.get("DataUltimaAlteracao") or payload.get("dataUltimaAlteracao") or ""
    items = payload.get("Nomenclaturas") or payload.get("nomenclaturas") or payload.get("dados") or []

    if not isinstance(items, list) or len(items) < 10000:
        raise SystemExit(f"Carga NCM inesperadamente pequena ou inválida: {len(items) if isinstance(items, list) else 'não-lista'}")

    generated_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for item in items:
        codigo_formatado = str(item.get("Codigo") or item.get("codigo") or "").strip()
        codigo = clean_code(codigo_formatado)
        if len(codigo) != 8:
            # O Classif contém níveis hierárquicos; para cadastro de produto
            # preservamos apenas NCMs completos de 8 dígitos.
            continue
        rows.append({
            "codigo": codigo,
            "codigo_formatado": codigo_formatado,
            "descricao": str(item.get("Descricao") or item.get("descricao") or "").strip(),
            "data_inicio": item.get("DataInicio") or item.get("dataInicio") or "",
            "data_fim": item.get("DataFim") or item.get("dataFim") or "",
            "tipo_orgao_ato_ini": item.get("TipoOrgaoAtoIni") or item.get("tipoOrgaoAtoIni") or "",
            "numero_ato_ini": item.get("NumeroAtoIni") or item.get("numeroAtoIni") or "",
            "ano_ato_ini": item.get("AnoAtoIni") or item.get("anoAtoIni") or "",
            "source_id": SOURCE_ID,
            "data_ultima_alteracao": data_ultima,
            "snapshot_gerado_em": generated_at,
        })

    if len(rows) < 10000:
        raise SystemExit(f"Poucos NCMs completos de 8 dígitos: {len(rows)}")

    rows.sort(key=lambda r: r["codigo"])
    NCM_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(NCM_DIR / "ncm_atual.csv", rows)
    write_csv(NCM_DIR / "ncm_vigente.csv", rows)

    snapshot_date = datetime.now(timezone.utc).date().isoformat()
    write_csv(NCM_DIR / "snapshots" / f"ncm_{snapshot_date}.csv", rows)

    meta = {
        "catalog": "ncm",
        "status": "OFFICIAL_CURRENT",
        "source_id": SOURCE_ID,
        "source_url": NCM_URL,
        "generated_at": generated_at,
        "data_ultima_alteracao": data_ultima,
        "records": len(rows),
        "contains_only_current_table": True,
        "historical_strategy": "repository_snapshots",
        "production_ready": True,
        "notes": [
            "Fonte oficial direta Receita Federal / Sistema Classif.",
            "Somente códigos NCM completos de 8 dígitos são distribuídos para cadastro de produtos.",
            "O endpoint oficial fornece apenas a tabela vigente; snapshots do repositório preservam o histórico de versões coletadas."
        ]
    }
    META_DIR.mkdir(parents=True, exist_ok=True)
    (META_DIR / "ncm.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"NCMs vigentes de 8 dígitos: {len(rows)}")
    print(f"Data última alteração na origem: {data_ultima}")


if __name__ == "__main__":
    main()
