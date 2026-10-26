# Dados de referência Servos — Fiscal e Produtos

Base pública, versionada e rastreável de dados fiscais usados pelo Lumina76 e de pré-cadastros comerciais compartilháveis entre os sistemas da Servos Tecnologia.

## Objetivo

Manter catálogos fiscais com origem, vigência e histórico preservado, prontos para consumo pelo Lumina76 sem transformar fontes de terceiros em autoridade fiscal.

Manter também um **catálogo mestre de produtos para acelerar implantações**, com descrições padronizadas, apresentações, categorias, códigos de barras conferidos e controle de origem de imagens. O catálogo comercial é independente da autoridade fiscal e não contém dados de clientes.

O nome e a URL do repositório, os caminhos NCM/CEST e os workflows fiscais permanecem os mesmos.

## Pré-cadastros de produtos

- [Documentação e contrato v1](produtos/README.md).
- [Catálogo mestre](produtos/catalogo.json) e [categorias](produtos/categorias.json).
- [Fontes consultadas](produtos/fontes.json).
- [Planilha CSV de revisão](produtos/exports/revisao.csv): todos os registros, incluindo pendências.
- [CSV de aprovados](produtos/exports/aprovados.csv): somente registros comercialmente conferidos.
- [Pacote piloto de bebidas](produtos/pacotes/bebidas-piloto.json).

Lote inicial `2026.10.26.1`: **50 apresentações coletadas, 3 aprovadas por conferência documental cruzada e 47 pendentes**. Nenhuma foto está liberada nesta versão. Os CSVs são genéricos; adaptadores de importação de sistemas ainda precisam ser implementados e homologados.

Validação e geração, sem acesso à rede: `python scripts/build_product_catalog.py`.
Conferência sem gravar: `python scripts/build_product_catalog.py --check`.

## Princípios

- Fontes oficiais são a autoridade normativa.
- Fontes auxiliares nunca substituem a autoridade fiscal.
- Atualização nunca apaga o passado.
- O Lumina76 deve continuar operando com o último catálogo local válido mesmo sem internet.
- Cada registro deve ser rastreável quanto à origem, UF e vigência.
- Catálogo nacional CEST e aplicabilidade estadual/ST são camadas diferentes.
- Identidade comercial, configuração fiscal e personalizações do cliente são camadas diferentes.
- GTIN não é inventado; dígito válido não comprova associação ao produto.
- Este repositório é público: publicar somente material compartilhável e imagens com uso esclarecido.

## Estrutura

### CEST

- `cest/cest_atual.csv`: catálogo CEST nacional normalizado vigente no snapshot publicado.
- `cest/cest_nacional.csv`: cópia nominal da base nacional.
- `cest/cest_ncm_atual.csv`: relacionamento CEST × NCM/SH.
- `cest/snapshots/`: snapshots históricos preservados.
- `cest/cest_ba_2026_segmento_03_piloto.csv`: camada BA já auditada para o segmento 03, mantida separadamente da base nacional.

### NCM

- `ncm/ncm_atual.csv`: NCM vigente normalizada para cadastro de produtos.
- `ncm/ncm_vigente.csv`: cópia nominal da base vigente.
- `ncm/snapshots/`: snapshots históricos preservados pelo repositório.
- `metadata/ncm.json`: metadados da última coleta oficial.

### Infraestrutura

- `metadata/`: metadados de versão, escopo e fontes.
- `scripts/`: geração reproduzível dos catálogos.
- `.github/workflows/`: atualização e validação automáticas.
- `CHANGELOG.md`: histórico das atualizações.

## Estado atual

### CEST

A base nacional foi materializada com **1.010 códigos CEST** e **1.223 relações CEST × NCM**, tendo o Convênio ICMS 142/2018/CONFAZ como autoridade normativa. A ingestão estruturada é feita por snapshot auxiliar do TabelasFiscais.com.br e essa distinção fica registrada em cada linha.

A camada de **aplicabilidade estadual da Bahia** ainda está em expansão e auditoria contra o Anexo 1 vigente do RICMS-BA. Portanto:

- `cest_atual.csv` pode ser usado como catálogo nacional de códigos/descrições CEST;
- ele não deve, sozinho, decidir se determinada mercadoria está sujeita a ST na Bahia;
- regras estaduais devem consultar a camada UF correspondente.

### NCM

A base NCM é ingerida **diretamente do endpoint oficial da Receita Federal / Sistema Classif / Portal Único Siscomex**, sem intermediário.

A primeira geração oficial contém **10.515 códigos NCM completos de 8 dígitos**.

A Receita fornece apenas a tabela vigente. Para preservar histórico operacional, este repositório grava snapshots próprios a cada atualização.

## Atualização

- CEST: workflow periódico com validação de volume e preservação de snapshots.
- NCM: workflow diário, pois a Receita informa que o arquivo oficial é atualizado automaticamente quando há alterações na NCM.
- Nenhuma atualização remove silenciosamente snapshots anteriores.
