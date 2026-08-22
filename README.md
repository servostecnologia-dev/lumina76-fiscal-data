# Lumina76 Fiscal Data

Base pública, versionada e rastreável de dados fiscais normalizados usados pelo Lumina76.

## Objetivo

Manter catálogos fiscais com origem, vigência e histórico preservado, prontos para consumo pelo Lumina76 sem transformar fontes de terceiros em autoridade fiscal.

## Princípios

- Fontes oficiais são a autoridade normativa.
- Fontes auxiliares nunca substituem a autoridade fiscal.
- Atualização nunca apaga o passado.
- O Lumina76 deve continuar operando com o último catálogo local válido mesmo sem internet.
- Cada registro deve ser rastreável quanto à origem, UF e vigência.
- Um catálogo só é promovido para uso de produção depois de cobertura e auditoria compatíveis com seu escopo.

## Estrutura

- `cest/`: catálogos CEST e snapshots históricos.
- `metadata/`: metadados de versão, escopo e fontes.
- `CHANGELOG.md`: histórico das atualizações.

## Estado atual

A base está em fase inicial de construção. O primeiro conjunto é um piloto parcial para a Bahia, segmento 03 (bebidas), extraído de fonte oficial da SEFAZ-BA.

Enquanto `metadata/catalog.json` indicar `production_ready: false`, os arquivos piloto não devem ser tratados como catálogo CEST completo do Lumina76.
