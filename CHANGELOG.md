# Changelog — Lumina76 Fiscal Data

## 2026-08-22 — NCM oficial integrado

- Criado `scripts/build_ncm_catalog.py` usando diretamente o endpoint oficial Receita Federal / Sistema Classif / Portal Único Siscomex.
- Primeira geração oficial: **10.515 códigos NCM completos de 8 dígitos**.
- Criados:
  - `ncm/ncm_atual.csv`;
  - `ncm/ncm_vigente.csv`;
  - `ncm/snapshots/ncm_2026-08-22.csv`;
  - `metadata/ncm.json`.
- Criado workflow diário de atualização e validação automática.
- O repositório passa a preservar histórico operacional por snapshots, pois a fonte oficial fornece apenas a tabela NCM vigente.

## 2026-08-22 — Expansão para catálogo nacional

- Materializado o catálogo nacional CEST com **1.010 registros**.
- Materializado o relacionamento CEST × NCM/SH com **1.223 registros**.
- Criados:
  - `cest/cest_atual.csv`;
  - `cest/cest_nacional.csv`;
  - `cest/cest_ncm_atual.csv`;
  - snapshot histórico em `cest/snapshots/`.
- CONFAZ / Convênio ICMS 142/2018 permanece como autoridade normativa nacional.
- TabelasFiscais.com.br foi registrado explicitamente apenas como fonte auxiliar de ingestão estruturada, nunca como autoridade fiscal.
- Criado gerador reproduzível em `scripts/build_cest_catalog.py`.
- Criado workflow mensal de geração e validação do catálogo.
- Mantida separação entre catálogo nacional CEST e camada de aplicabilidade estadual/ST.
- O CEST `03.005.04` está presente na base nacional e também na camada BA já auditada para o segmento 03.

## 2026-08-22 — Fundação do catálogo

- Criada a estrutura inicial de dados fiscais versionados.
- Registradas as primeiras fontes oficiais:
  - SEFAZ-BA / Anexo 1 do RICMS-BA vigente em 2026;
  - Receita Federal / Classif para NCM vigente;
  - CONFAZ / Convênio ICMS 142/2018 como autoridade normativa nacional do CEST/ST.
- Criado o primeiro catálogo piloto parcial para a Bahia, segmento 03 (bebidas).
- Incluído o CEST `03.005.04` para água mineral em demais embalagens descartáveis, aplicável ao caso de garrafa PET descartável analisado na Expofeira.

## Regra de manutenção

- Atualizações futuras devem preservar snapshots históricos.
- Alterações devem registrar fonte e vigência.
- Nenhum registro histórico será apagado silenciosamente.
- Catálogo nacional e aplicabilidade estadual devem permanecer conceitualmente separados.
