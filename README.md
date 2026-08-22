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
- Catálogo nacional CEST e aplicabilidade estadual/ST são camadas diferentes.

## Estrutura

- `cest/cest_atual.csv`: catálogo CEST nacional normalizado vigente no snapshot publicado.
- `cest/cest_nacional.csv`: cópia nominal da base nacional.
- `cest/cest_ncm_atual.csv`: relacionamento CEST × NCM/SH.
- `cest/snapshots/`: snapshots históricos preservados.
- `cest/cest_ba_2026_segmento_03_piloto.csv`: camada BA já auditada para o segmento 03, mantida separadamente da base nacional.
- `metadata/`: metadados de versão, escopo e fontes.
- `scripts/`: geração reproduzível do catálogo.
- `CHANGELOG.md`: histórico das atualizações.

## Estado atual

A base nacional foi materializada com **1.010 códigos CEST** e **1.223 relações CEST × NCM**, tendo o Convênio ICMS 142/2018/CONFAZ como autoridade normativa. A ingestão estruturada é feita por snapshot auxiliar do TabelasFiscais.com.br e essa distinção fica registrada em cada linha.

A camada de **aplicabilidade estadual da Bahia** ainda está em expansão e auditoria contra o Anexo 1 vigente do RICMS-BA. Portanto:

- `cest_atual.csv` pode ser usado como catálogo nacional de códigos/descrições CEST;
- ele não deve, sozinho, decidir se determinada mercadoria está sujeita a ST na Bahia;
- regras estaduais devem consultar a camada UF correspondente.

## Atualização

O workflow `Build CEST catalog` roda mensalmente e também pode ser disparado manualmente. Cada geração preserva snapshot histórico e bloqueia cargas anormalmente pequenas.
