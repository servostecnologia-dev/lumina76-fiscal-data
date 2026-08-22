#!/usr/bin/env python3
"""Gera os catálogos CEST distribuídos pelo repositório Lumina76 Fiscal Data.

Autoridade normativa: CONFAZ / Convênio ICMS 142/2018 e alterações.
Fonte de ingestão estruturada: TabelasFiscais.com.br, que publica snapshots
regenerados a partir de fontes oficiais. O repositório mantém essa distinção
explícita: autoridade normativa != transportador/normalizador dos dados.
"""
from __future__ import annotations

import csv
import io
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CEST_DIR = ROOT / "cest"
META_DIR = ROOT / "metadata"

CEST_JSON_URL = "https://tabelasfiscais.com.br/public/downloads/cest.json"
CEST_NCM_JSON_URL = "https://tabelasfiscais.com.br/public/downloads/cest_ncm.json"
AUTHORITY_SOURCE = "CONFAZ_CV142_18"
INGESTION_SOURCE = "TABELASFISCAIS_SNAPSHOT"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Lumina76-Fiscal-Data/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def normalize_cest(cest: str) -> str:
    return "".join(ch for ch in cest if ch.isdigit())


def write_csv(path: Path, headers: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    cest_payload = get_json(CEST_JSON_URL)
    ncm_payload = get_json(CEST_NCM_JSON_URL)

    generated_at = cest_payload.get("gerado_em") or datetime.now(timezone.utc).isoformat()
    cest_data = cest_payload.get("dados", cest_payload if isinstance(cest_payload, list) else [])
    ncm_data = ncm_payload.get("dados", ncm_payload if isinstance(ncm_payload, list) else [])

    if len(cest_data) < 900:
        raise SystemExit(f"Carga CEST inesperadamente pequena: {len(cest_data)} registros")

    rows = []
    for item in cest_data:
        cest = (item.get("cest") or "").strip()
        if not cest:
            continue
        rows.append({
            "cest": cest,
            "cest_normalizado": normalize_cest(cest),
            "descricao": (item.get("descricao") or "").strip(),
            "segmento": (item.get("segmento") or "").strip(),
            "status": "VIGENTE_SNAPSHOT",
            "vigencia_inicio": item.get("vigencia_inicio") or item.get("valid_from") or "",
            "vigencia_fim": item.get("vigencia_fim") or item.get("valid_to") or "",
            "authority_source_id": AUTHORITY_SOURCE,
            "ingestion_source_id": INGESTION_SOURCE,
            "snapshot_gerado_em": generated_at,
        })

    rows.sort(key=lambda r: r["cest_normalizado"])
    headers = [
        "cest", "cest_normalizado", "descricao", "segmento", "status",
        "vigencia_inicio", "vigencia_fim", "authority_source_id",
        "ingestion_source_id", "snapshot_gerado_em",
    ]

    current = CEST_DIR / "cest_atual.csv"
    national = CEST_DIR / "cest_nacional.csv"
    snapshot_date = generated_at[:10] if generated_at else datetime.now().date().isoformat()
    snapshot = CEST_DIR / "snapshots" / f"cest_nacional_{snapshot_date}.csv"
    write_csv(current, headers, rows)
    write_csv(national, headers, rows)
    write_csv(snapshot, headers, rows)

    # Mapeamento CEST x NCM em arquivo separado para evitar perda de cardinalidade.
    map_rows = []
    if isinstance(ncm_data, list):
        for item in ncm_data:
            cest = str(item.get("cest") or item.get("CEST") or "").strip()
            ncm = str(item.get("ncm") or item.get("NCM") or item.get("ncm_sh") or "").strip()
            if not cest or not ncm:
                continue
            map_rows.append({
                "cest": cest,
                "cest_normalizado": normalize_cest(cest),
                "ncm_sh": ncm,
                "authority_source_id": AUTHORITY_SOURCE,
                "ingestion_source_id": INGESTION_SOURCE,
                "snapshot_gerado_em": generated_at,
            })
    map_rows.sort(key=lambda r: (r["cest_normalizado"], r["ncm_sh"]))
    write_csv(
        CEST_DIR / "cest_ncm_atual.csv",
        ["cest", "cest_normalizado", "ncm_sh", "authority_source_id", "ingestion_source_id", "snapshot_gerado_em"],
        map_rows,
    )

    metadata = {
        "catalog": "lumina76-fiscal-data",
        "status": "NATIONAL_BASE_READY_BA_OVERLAY_PARTIAL",
        "generated_at": generated_at,
        "national_cest_records": len(rows),
        "cest_ncm_records": len(map_rows),
        "authority_source": AUTHORITY_SOURCE,
        "ingestion_source": INGESTION_SOURCE,
        "production_ready_for_national_cest_catalog": True,
        "production_ready_for_uf_applicability": False,
        "notes": [
            "cest_atual.csv representa o catálogo CEST nacional normalizado.",
            "Aplicabilidade estadual/ST deve ser tratada em camadas UF separadas.",
            "A camada BA ainda está em expansão/auditoria contra o Anexo 1 do RICMS-BA vigente.",
        ],
    }
    META_DIR.mkdir(parents=True, exist_ok=True)
    (META_DIR / "catalog.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"CEST nacional: {len(rows)} registros")
    print(f"CEST x NCM: {len(map_rows)} registros")
    print(f"Snapshot: {snapshot}")


if __name__ == "__main__":
    main()
