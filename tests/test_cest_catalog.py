from __future__ import annotations

import json
from pathlib import Path
import urllib.error

import pytest

from scripts import build_cest_catalog as catalog


class _Response:
    def __init__(self, payload: object):
        self.raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.raw


def _payloads(count: int = 3, relation_count: int = 3):
    cest = {
        "gerado_em": "2026-11-06T12:00:00Z",
        "dados": [
            {"cest": f"03.{index:03d}.00", "descricao": f"CEST {index}", "segmento": "03"}
            for index in range(1, count + 1)
        ],
    }
    relations = {
        "gerado_em": "2026-11-06T11:00:00Z",
        "dados": [
            {"cest": f"03.{((index - 1) % count) + 1:03d}.00", "ncm": f"22{index:06d}"}
            for index in range(1, relation_count + 1)
        ],
    }
    return cest, relations


def _candidate(count: int = 3, relation_count: int = 3):
    cest, relations = _payloads(count, relation_count)
    return catalog.build_candidate(cest, relations, cest_attempts=1, ncm_attempts=1)


def test_http_523_recupera_com_backoff_limitado() -> None:
    calls = []
    sleeps = []
    payload, _ = _payloads()

    def opener(*_args, **_kwargs):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.HTTPError("https://source.invalid", 523, "origin down", {}, None)
        return _Response(payload)

    result = catalog.get_json(
        "https://source.invalid",
        max_attempts=4,
        base_delay_seconds=0.25,
        sleep=sleeps.append,
        opener=opener,
    )

    assert result.attempts == 3
    assert sleeps == [0.25, 0.5]


def test_http_nao_transitorio_nao_e_repetido() -> None:
    calls = []

    def opener(*_args, **_kwargs):
        calls.append(1)
        raise urllib.error.HTTPError("https://source.invalid", 404, "not found", {}, None)

    with pytest.raises(catalog.CatalogSourceError) as exc:
        catalog.get_json("https://source.invalid", sleep=lambda _seconds: None, opener=opener)

    assert exc.value.transient is False
    assert exc.value.status == 404
    assert len(calls) == 1


def test_esgotamento_523_informa_tentativas_sem_publicar() -> None:
    def opener(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://source.invalid", 523, "origin down", {}, None)

    with pytest.raises(catalog.CatalogSourceError) as exc:
        catalog.get_json(
            "https://source.invalid",
            max_attempts=3,
            base_delay_seconds=0,
            sleep=lambda _seconds: None,
            opener=opener,
        )

    assert exc.value.attempts == 3
    assert exc.value.transient is True
    assert exc.value.status == 523


def test_conteudo_invalido_regressivo_ou_sem_proveniencia_e_bloqueado(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(catalog, "MIN_CEST_ROWS", 2)
    monkeypatch.setattr(catalog, "MIN_CEST_NCM_ROWS", 2)
    rows, relations, _metadata = _candidate(3, 3)
    (tmp_path / "metadata").mkdir()
    (tmp_path / "metadata" / "catalog.json").write_text(
        json.dumps({"national_cest_records": 4, "cest_ncm_records": 4}), encoding="utf-8"
    )

    with pytest.raises(catalog.CatalogValidationError, match="regressivo"):
        catalog.validate_candidate(tmp_path, rows, relations)

    cest, relation_payload = _payloads()
    del cest["gerado_em"]
    with pytest.raises(catalog.CatalogValidationError, match="proveniencia"):
        catalog.build_candidate(cest, relation_payload, cest_attempts=1, ncm_attempts=1)


def test_promocao_preserva_todo_snapshot_em_falha_injetada(tmp_path: Path, monkeypatch) -> None:
    first = tmp_path / "cest_atual.csv"
    second = tmp_path / "cest_ncm_atual.csv"
    first.write_bytes(b"primeiro-valido")
    second.write_bytes(b"segundo-valido")
    original_write = catalog._atomic_write_bytes
    failed = {"value": False}

    def fail_once(path: Path, content: bytes) -> None:
        if path == second and not failed["value"]:
            failed["value"] = True
            raise OSError("falha injetada")
        original_write(path, content)

    monkeypatch.setattr(catalog, "_atomic_write_bytes", fail_once)
    with pytest.raises(OSError, match="falha injetada"):
        catalog.promote_candidate({first: b"primeiro-novo", second: b"segundo-novo"})

    assert first.read_bytes() == b"primeiro-valido"
    assert second.read_bytes() == b"segundo-valido"


def test_candidato_valido_promove_e_repeticao_e_idempotente(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(catalog, "MIN_CEST_ROWS", 2)
    monkeypatch.setattr(catalog, "MIN_CEST_NCM_ROWS", 2)
    rows, relations, metadata = _candidate(3, 3)

    catalog.validate_candidate(tmp_path, rows, relations)
    files = catalog.candidate_files(tmp_path, rows, relations, metadata)
    catalog.promote_candidate(files)
    first = {path: path.read_bytes() for path in files}
    catalog.promote_candidate(files)
    second = {path: path.read_bytes() for path in files}

    assert first == second
    assert metadata["source_urls"]["cest"] == catalog.CEST_JSON_URL
    assert metadata["fetch_attempts"] == {"cest": 1, "cest_ncm": 1}
