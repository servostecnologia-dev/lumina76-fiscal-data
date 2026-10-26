# Catálogo mestre de produtos Servos

Pré-cadastros compartilháveis para reduzir o trabalho de implantação. Cada registro identifica **uma apresentação comercial**, não um preço, estoque ou cadastro de cliente.

## Primeira versão

`2026.10.26.1`, coletada em 26/10/2026: 24 refrigerantes, 8 tônicas/misturadores, 8 cervejas, 6 águas e 4 bebidas de fruta. Categorias de vinhos e energéticos já existem, sem itens neste lote.

São 50 registros: 3 aprovados comercialmente e 47 pendentes. Há 0 imagens liberadas. A cobertura inicial foi concentrada nos portfólios da FEMSA pela disponibilidade de dados estruturados; não representa todo o mercado nem disponibilidade na Bahia.

## Arquivos

| Caminho | Função |
| --- | --- |
| `catalogo.json` | Fonte canônica dos produtos |
| `categorias.json` | Grupos com identificadores estáveis e hierarquia |
| `fontes.json` | URLs, origem, região, data e método de consulta |
| `pacotes/*.json` | Seleções editoriais por identificador de produto |
| `exports/revisao.csv` | Todos os registros e suas pendências; não importar em produção |
| `exports/aprovados.csv` | Somente registros aprovados |
| `exports/pacote-*.csv` | Interseção do pacote com os aprovados |
| `exports/manifest.json` | Versão, contagens e hashes das exportações |

JSONs são editáveis e versionados no Git. CSVs e manifesto são derivados: regenerar, nunca editar isoladamente.

## Contrato v1.0.0

- `id`: identificador permanente `SVP-000001`. Nunca renumerar/reutilizar; para retirar um item, marcar `descontinuado`.
- `descricao` e `descricao_curta`: redação padronizada da Servos, sem copiar textos publicitários. A descrição curta não presume limite universal: o adaptador deverá respeitar o destino.
- `marca`, `variante`, `conteudo_ml`, `embalagem`, `unidade_venda`: identidade da apresentação. Volume é inteiro em ml; v1 trata bebidas vendidas em `UN`.
- `categoria_id`: referência às categorias. Cada cliente pode mapear os grupos para seu próprio cadastro.
- `gtins`: lista de códigos **conferidos**, como texto. Preservar zeros; aceitar GTIN-8/12/13/14 com dígito válido. Comparar com preenchimento à esquerda até 14 posições para detectar duplicação.
- `codigos_candidatos`: códigos exatamente como observados, com fonte e escopo ainda não confirmado. Nunca migrar automaticamente para `gtins`, completar zeros por suposição ou construir código a partir de outro.
- `logistica_observada`: quantidade de unidades do agrupamento informado na fonte. Não transforma o produto em caixa nem comprova código do pack. Caixas comercializadas como itens próprios exigirão registros e vínculos conferidos separadamente.
- `evidencias`: origem por conjunto de campos e nota de interpretação. Fonte regional ou histórica é identificada em `fontes.json`.
- `status`: `coletado`, `pendente`, `aprovado` ou `descontinuado`.
- `revisao`: data, responsável, método e escopo da conferência comercial. Não implica aprovação pelo fabricante, GS1 ou homologação fiscal.
- `imagem`: status, URL, fonte e condição de uso. Uma foto ausente não impede aprovação comercial; foto pendente nunca é exportada.
- `aliases`, `pendencias`, `criado_em`, `atualizado_em`: busca alternativa e rastreabilidade. Datas em ISO 8601.

`schema_version` controla o contrato; `catalog_version` identifica o lote. Mudanças de apresentação exigem outro produto; correções mantêm o ID com histórico no Git. Corrigir evidências e atualizar versão/data quando o conteúdo mudar.

## Coleta e aprovação

1. Localizar apresentação e origem, priorizando fabricante/distribuidor; registrar dados factuais e data.
2. Marcar como pendente enquanto houver dúvida sobre apresentação, atualidade ou código da unidade.
3. Conferir GTIN e apresentação em duas fontes distintas, ao menos uma do fabricante/distribuidor. Registrar método e responsável. O validador confere referências; a independência e a qualidade das fontes exigem revisão editorial.
4. Aprovar apenas sem pendências comerciais. Fotos podem permanecer ausentes. Consultas na GS1 ou inspeção da embalagem poderão reforçar a revisão, mas não foram feitas neste lote.
5. Gerar exportações e executar os testes. Nunca remover silenciosamente o histórico.

Neste lote, páginas indexadas dos portfólios foram usadas como evidência de coleta: algumas páginas dinâmicas não disponibilizaram o conteúdo na abertura direta. Esse método está explícito nas fontes. O portfólio de colas de 2024 é histórico; seus itens permanecem pendentes de atualidade, salvo os dois cruzados com páginas atuais de unidades. Os três aprovados foram cruzados com páginas abertas de varejistas/distribuidor que exibem apresentação e código.

Não copiar fotos de pesquisa automaticamente. Priorizar fotografia própria ou material disponibilizado com condição de uso compatível, registrando a origem e a liberação. Por enquanto `imagem.url` é nulo em todos os itens.

## Uso na implantação

Selecionar pacote → revisar produtos/grupos → conferir duplicidades no cliente por ID Servos e GTIN → preencher preços e configurações locais → importar usando adaptador homologado.

Os CSVs UTF-8 com BOM e separador `;` são uma interface genérica. **Não importar diretamente** sem mapear os campos do sistema de destino. No Excel, importar as colunas de código como texto para preservar zeros. A barra `|` separa múltiplos GTINs; o adaptador deverá desmembrá-los conforme o destino.

Preservar o ID e a versão de origem no cliente. Atualizações futuras devem mostrar diferenças e preservar alterações locais. Este repositório ainda não implementa a tela de seleção, o importador nem a sincronização de clientes.

Não há preço, custo, estoque, credenciais ou dados de clientes. Não há NCM/CEST inferidos, CFOP, CST/CSOSN ou tributação aplicada. A configuração fiscal precisa de revisão independente.

## Verificação

```bash
python scripts/build_product_catalog.py
python scripts/build_product_catalog.py --check
python -m unittest discover -s tests -v
```

O gerador opera offline com Python 3.11+ e biblioteca padrão. Valida IDs, categorias/ciclos, fontes, datas, GTINs, aprovação, imagens e pacotes. `--check` exige que as exportações correspondam aos dados atuais. O workflow `validate-products.yml` executa essas verificações sem atualizar dados ou publicar automaticamente.

Próximos lotes: conferir os 47 pendentes, ampliar marcas e fornecedores relevantes à Bahia, coletar imagens próprias/liberadas e homologar primeiro um adaptador real de implantação. Expandir vinhos com cuidado adicional para safra, origem, volume e variações de GTIN.
