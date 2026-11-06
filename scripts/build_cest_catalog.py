#!/usr/bin/env python3
"""Gera e promove os catalogos CEST sem destruir o ultimo snapshot valido."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import json
import os
import socket
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
CEST_DIR = ROOT / "cest"
META_DIR = ROOT / "metadata"

CEST_JSON_URL = "https://tabelasfiscais.com.br/public/downloads/cest.json"
CEST_NCM_JSON_URL = "https://tabelasfiscais.com.br/public/downloads/cest_ncm.json"
AUTHORITY_SOURCE = "CONFAZ_CV142_18"
INGESTION_SOURCE = "TABELASFISCAIS_SNAPSHOT"
MIN_CEST_ROWS = 900
MIN_CEST_NCM_ROWS = 500
TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}


class CatalogSourceError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        url: str,
        attempts: int,
        status: int | None,
        transient: bool,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.attempts = attempts
        self.status = status
        self.transient = transient


class CatalogValidationError(ValueError):
    pass


@dataclass(frozen=True)
class FetchResult:
    payload: object
    attempts: int


def _is_transient_status(status: int) -> bool:
    return status in TRANSIENT_HTTP or 520 <= status <= 527


def get_json(
    url: str,
    *,
    max_attempts: int = 4,
    base_delay_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    opener: Callable[..., object] = urllib.request.urlopen,
) -> FetchResult:
    """Baixa JSON com retentativa limitada apenas para falhas transitórias."""

    attempts = max(1, int(max_attempts))
    last_status: int | None = None
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(url, headers={"User-Agent": "Lumina76-Fiscal-Data/1.0"})
        try:
            with opener(req, timeout=60) as response:  # type: ignore[attr-defined]
                raw = response.read()  # type: ignore[attr-defined]
            payload = json.loads(raw.decode("utf-8-sig", errors="strict"))
            return FetchResult(payload=payload, attempts=attempt)
        except urllib.error.HTTPError as exc:
            last_status = int(exc.code or 0)
            transient = _is_transient_status(last_status)
            if not transient:
                raise CatalogSourceError(
                    f"Fonte CEST recusou a coleta com HTTP {last_status}; falha nao transitoria.",
                    url=url,
                    attempts=attempt,
                    status=last_status,
                    transient=False,
                ) from exc
            cause: Exception = exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            cause = exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CatalogSourceError(
                "Fonte CEST retornou conteudo que nao e JSON UTF-8 valido.",
                url=url,
                attempts=attempt,
                status=None,
                transient=False,
            ) from exc

        if attempt >= attempts:
            status_detail = f" HTTP {last_status}" if last_status else ""
            raise CatalogSourceError(
                f"Fonte CEST indisponivel apos {attempts} tentativas.{status_detail}",
                url=url,
                attempts=attempts,
                status=last_status,
                transient=True,
            ) from cause
        sleep(float(base_delay_seconds) * (2 ** (attempt - 1)))

    raise AssertionError("Fluxo de retentativa inconsistente")


def normalize_cest(cest: str) -> str:
    return "".join(ch for ch in str(cest or "") if ch.isdigit())


def normalize_ncm_sh(ncm: str) -> str:
    return "".join(ch for ch in str(ncm or "") if ch.isdigit())


def _csv_bytes(headers: list[str], rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=headers,
        delimiter=";",
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _payload_rows(payload: object, *, label: str) -> tuple[str, list[dict]]:
    if not isinstance(payload, dict):
        raise CatalogValidationError(f"{label}: envelope JSON invalido.")
    generated_at = str(payload.get("gerado_em") or "").strip()
    data = payload.get("dados")
    if not generated_at:
        raise CatalogValidationError(f"{label}: gerado_em ausente; proveniencia insuficiente.")
    if not isinstance(data, list):
        raise CatalogValidationError(f"{label}: lista dados ausente ou invalida.")
    return generated_at, data


def build_candidate(
    cest_payload: object,
    ncm_payload: object,
    *,
    cest_attempts: int,
    ncm_attempts: int,
) -> tuple[list[dict], list[dict], dict]:
    generated_at, cest_data = _payload_rows(cest_payload, label="CEST")
    relation_generated_at, ncm_data = _payload_rows(ncm_payload, label="CEST x NCM")

    rows: list[dict] = []
    seen_cest: set[str] = set()
    for item in cest_data:
        if not isinstance(item, dict):
            raise CatalogValidationError("CEST: registro nao e um objeto.")
        formatted = str(item.get("cest") or "").strip()
        normalized = normalize_cest(formatted)
        description = str(item.get("descricao") or "").strip()
        if len(normalized) != 7 or not description:
            raise CatalogValidationError(f"CEST: registro invalido ({normalized or 'sem codigo'}).")
        if normalized in seen_cest:
            raise CatalogValidationError(f"CEST: codigo duplicado ({normalized}).")
        seen_cest.add(normalized)
        rows.append(
            {
                "cest": formatted,
                "cest_normalizado": normalized,
                "descricao": description,
                "segmento": str(item.get("segmento") or "").strip(),
                "status": "VIGENTE_SNAPSHOT",
                "vigencia_inicio": item.get("vigencia_inicio") or item.get("valid_from") or "",
                "vigencia_fim": item.get("vigencia_fim") or item.get("valid_to") or "",
                "authority_source_id": AUTHORITY_SOURCE,
                "ingestion_source_id": INGESTION_SOURCE,
                "snapshot_gerado_em": generated_at,
            }
        )
    rows.sort(key=lambda row: row["cest_normalizado"])

    relations: list[dict] = []
    seen_relations: set[tuple[str, str]] = set()
    for item in ncm_data:
        if not isinstance(item, dict):
            raise CatalogValidationError("CEST x NCM: registro nao e um objeto.")
        formatted = str(item.get("cest") or item.get("CEST") or "").strip()
        normalized = normalize_cest(formatted)
        ncm = str(item.get("ncm") or item.get("NCM") or item.get("ncm_sh") or "").strip()
        normalized_ncm = normalize_ncm_sh(ncm)
        key = (normalized, normalized_ncm)
        if normalized not in seen_cest:
            raise CatalogValidationError(f"CEST x NCM: codigo CEST inexistente ({normalized}).")
        if not (2 <= len(normalized_ncm) <= 8):
            raise CatalogValidationError(f"CEST x NCM: NCM/SH invalido para {normalized}.")
        if key in seen_relations:
            raise CatalogValidationError(f"CEST x NCM: relacao duplicada ({normalized}/{normalized_ncm}).")
        seen_relations.add(key)
        relations.append(
            {
                "cest": formatted,
                "cest_normalizado": normalized,
                "ncm_sh": ncm,
                "authority_source_id": AUTHORITY_SOURCE,
                "ingestion_source_id": INGESTION_SOURCE,
                "snapshot_gerado_em": generated_at,
            }
        )
    relations.sort(key=lambda row: (row["cest_normalizado"], normalize_ncm_sh(row["ncm_sh"])))

    metadata = {
        "catalog": "lumina76-fiscal-data",
        "status": "NATIONAL_BASE_READY_BA_OVERLAY_PARTIAL",
        "generated_at": generated_at,
        "relation_source_generated_at": relation_generated_at,
        "national_cest_records": len(rows),
        "cest_ncm_records": len(relations),
        "authority_source": AUTHORITY_SOURCE,
        "ingestion_source": INGESTION_SOURCE,
        "source_urls": {"cest": CEST_JSON_URL, "cest_ncm": CEST_NCM_JSON_URL},
        "fetch_attempts": {"cest": int(cest_attempts), "cest_ncm": int(ncm_attempts)},
        "production_ready_for_national_cest_catalog": True,
        "production_ready_for_uf_applicability": False,
        "notes": [
            "cest_atual.csv representa o catálogo CEST nacional normalizado.",
            "Aplicabilidade estadual/ST deve ser tratada em camadas UF separadas.",
            "A camada BA ainda está em expansão/auditoria contra o Anexo 1 do RICMS-BA vigente.",
        ],
    }
    return rows, relations, metadata


def _existing_counts(root: Path) -> tuple[int, int]:
    path = root / "metadata" / "catalog.json"
    if not path.exists():
        return 0, 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return int(payload.get("national_cest_records") or 0), int(payload.get("cest_ncm_records") or 0)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise CatalogValidationError("Metadados atuais invalidos; promocao bloqueada.") from exc


def validate_candidate(root: Path, rows: list[dict], relations: list[dict]) -> None:
    if len(rows) < MIN_CEST_ROWS:
        raise CatalogValidationError(f"Carga CEST inesperadamente pequena: {len(rows)} registros.")
    if len(relations) < MIN_CEST_NCM_ROWS:
        raise CatalogValidationError(f"Carga CEST x NCM inesperadamente pequena: {len(relations)} registros.")
    old_cest, old_relations = _existing_counts(root)
    if old_cest and len(rows) < old_cest:
        raise CatalogValidationError(f"Volume CEST regressivo: {len(rows)} < {old_cest}.")
    if old_relations and len(relations) < old_relations:
        raise CatalogValidationError(f"Volume CEST x NCM regressivo: {len(relations)} < {old_relations}.")


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def promote_candidate(files: dict[Path, bytes]) -> None:
    """Promove o conjunto e restaura todos os destinos em qualquer falha."""

    originals = {path: (path.read_bytes() if path.exists() else None) for path in files}
    touched: list[Path] = []
    try:
        for path, content in files.items():
            _atomic_write_bytes(path, content)
            touched.append(path)
    except Exception as exc:
        rollback_errors: list[str] = []
        for path in reversed(touched):
            try:
                previous = originals[path]
                if previous is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write_bytes(path, previous)
            except Exception as rollback_exc:  # pragma: no cover - falha dupla de filesystem
                rollback_errors.append(f"{path.name}: {type(rollback_exc).__name__}")
        if rollback_errors:
            raise RuntimeError(
                "Promocao falhou e o rollback do catalogo ficou incompleto: " + ", ".join(rollback_errors)
            ) from exc
        raise


def candidate_files(root: Path, rows: list[dict], relations: list[dict], metadata: dict) -> dict[Path, bytes]:
    cest_headers = [
        "cest", "cest_normalizado", "descricao", "segmento", "status",
        "vigencia_inicio", "vigencia_fim", "authority_source_id",
        "ingestion_source_id", "snapshot_gerado_em",
    ]
    relation_headers = [
        "cest", "cest_normalizado", "ncm_sh", "authority_source_id",
        "ingestion_source_id", "snapshot_gerado_em",
    ]
    current_bytes = _csv_bytes(cest_headers, rows)
    relation_bytes = _csv_bytes(relation_headers, relations)
    snapshot_date = str(metadata["generated_at"])[:10]
    if len(snapshot_date) != 10:
        raise CatalogValidationError("Data do snapshot CEST invalida.")
    snapshot_path = root / "cest" / "snapshots" / f"cest_nacional_{snapshot_date}.csv"
    if snapshot_path.exists() and snapshot_path.read_bytes() != current_bytes:
        raise CatalogValidationError(f"Snapshot {snapshot_path.name} ja existe com conteudo divergente.")
    return {
        root / "cest" / "cest_atual.csv": current_bytes,
        root / "cest" / "cest_nacional.csv": current_bytes,
        root / "cest" / "cest_ncm_atual.csv": relation_bytes,
        snapshot_path: current_bytes,
        root / "metadata" / "catalog.json": (
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8"),
    }


def main() -> None:
    cest_result = get_json(CEST_JSON_URL)
    relation_result = get_json(CEST_NCM_JSON_URL)
    rows, relations, metadata = build_candidate(
        cest_result.payload,
        relation_result.payload,
        cest_attempts=cest_result.attempts,
        ncm_attempts=relation_result.attempts,
    )
    validate_candidate(ROOT, rows, relations)
    files = candidate_files(ROOT, rows, relations, metadata)
    promote_candidate(files)

    print(f"CEST nacional validado e promovido: {len(rows)} registros")
    print(f"CEST x NCM validado e promovido: {len(relations)} registros")
    print(f"Proveniencia: {AUTHORITY_SOURCE} via {INGESTION_SOURCE}")


if __name__ == "__main__":
    main()
