#!/usr/bin/env python3
"""Valida catálogo Servos e gera CSVs determinísticos, sem rede/dependências."""
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def gtin_valid(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12,14})', value):
        return False
    if set(value) == {'0'}:
        return False
    total = sum(int(n) * (3 if i % 2 == 0 else 1) for i, n in enumerate(reversed(value[:-1])))
    return (10 - total % 10) % 10 == int(value[-1])


def unique_index(records, label):
    require(isinstance(records, list), f'{label}: deve ser lista')
    index = {}
    for record in records:
        require(isinstance(record, dict), f'{label}: registro inválido')
        key = record.get('id')
        require(isinstance(key, str) and key.strip(), f'{label}: id vazio')
        require(key not in index, f'{label}: id duplicado {key}')
        index[key] = record
    return index


def validate(catalog, categories, sources, packages):
    for doc in [catalog, categories, sources, *packages]:
        require(doc.get('schema_version') == '1.0.0', 'schema_version incompatível')
    require(isinstance(catalog.get('catalog_version'), str) and catalog['catalog_version'], 'versão ausente')
    cats = unique_index(categories['categorias'], 'categorias')
    src = unique_index(sources['fontes'], 'fontes')
    items = unique_index(catalog['produtos'], 'produtos')
    for key, cat in cats.items():
        require(isinstance(cat.get('nome'), str) and cat['nome'].strip(), f'{key}: nome ausente')
        seen = {key}
        parent = cat.get('pai_id')
        while parent is not None:
            require(parent in cats and parent not in seen, f'{key}: pai inexistente ou ciclo')
            seen.add(parent)
            parent = cats[parent].get('pai_id')
    for key, source in src.items():
        url = urlparse(source.get('url', ''))
        require(url.scheme == 'https' and bool(url.netloc), f'{key}: URL inválida')
        date.fromisoformat(source['consultado_em'])
    owners = {}
    required = {'id','descricao','descricao_curta','marca','variante','categoria_id','conteudo_ml','embalagem','unidade_venda','gtins','codigos_candidatos','logistica_observada','aliases','status','revisao','evidencias','imagem','pendencias','criado_em','atualizado_em'}
    for key, product in items.items():
        require(set(product) == required, f'{key}: campos ausentes ou desconhecidos')
        require(re.fullmatch(r'SVP-[0-9]{6}', key), f'{key}: id inválido')
        for field in ('descricao','descricao_curta','marca','variante'):
            require(isinstance(product[field], str) and product[field].strip(), f'{key}: {field} vazio')
        require(product['categoria_id'] in cats, f'{key}: categoria inexistente')
        require(type(product['conteudo_ml']) is int and product['conteudo_ml'] > 0, f'{key}: volume inválido')
        require(product['embalagem'] in {'lata','garrafa_pet','long_neck','cartonada','garrafa_vidro','barril','copo'}, f'{key}: embalagem inválida')
        require(product['unidade_venda'] == 'UN', f'{key}: unidade inválida para v1')
        require(product['status'] in {'coletado','pendente','aprovado','descontinuado'}, f'{key}: status inválido')
        for field in ('gtins','codigos_candidatos','aliases','evidencias','pendencias'):
            require(isinstance(product[field], list), f'{key}: {field} deve ser lista')
        for field in ('aliases','pendencias'):
            require(all(isinstance(v, str) and v for v in product[field]), f'{key}: {field} inválido')
        date.fromisoformat(product['criado_em'])
        date.fromisoformat(product['atualizado_em'])
        require(product['criado_em'] <= product['atualizado_em'], f'{key}: datas invertidas')
        evidence_sources = set()
        require(product['evidencias'], f'{key}: evidência ausente')
        for evidence in product['evidencias']:
            require(evidence['fonte_id'] in src and evidence['campos'], f'{key}: evidência inválida')
            evidence_sources.add(evidence['fonte_id'])
        for candidate in product['codigos_candidatos']:
            require(isinstance(candidate['valor_observado'], str) and candidate['valor_observado'], f'{key}: candidato deve ser texto')
            require(candidate['fonte_id'] in evidence_sources, f'{key}: candidato sem evidência')
            require(candidate['escopo'] == 'nao_confirmado', f'{key}: escopo candidato inválido')
        logistics = product['logistica_observada']
        require(type(logistics['quantidade']) is int and logistics['quantidade'] > 0, f'{key}: logística inválida')
        require(logistics['fonte_id'] in evidence_sources, f'{key}: logística sem evidência')
        for gtin in product['gtins']:
            require(gtin_valid(gtin), f'{key}: GTIN inválido {gtin}')
            normalized = gtin.zfill(14)
            require(normalized not in owners, f'{key}: GTIN duplicado com {owners.get(normalized)}')
            owners[normalized] = key
            require(any('gtins' in e['campos'] for e in product['evidencias']), f'{key}: GTIN sem evidência')
        image = product['imagem']
        require(set(image) == {'status','url','fonte_id','condicao_uso'}, f'{key}: campos de imagem inválidos')
        require(image['status'] in {'pendente','referencia','liberada'}, f'{key}: imagem inválida')
        if image['status'] in {'referencia','liberada'}:
            parsed = urlparse(image['url'] or '')
            require(parsed.scheme == 'https' and bool(parsed.netloc), f'{key}: imagem sem URL válida')
            require(image['fonte_id'] in src and bool(image['condicao_uso']), f'{key}: imagem sem origem/condição de uso')
        else:
            require(image['url'] is None, f'{key}: foto pendente não pode ser distribuída')
        if product['status'] == 'aprovado':
            require(product['gtins'] and len(evidence_sources) >= 2, f'{key}: aprovação exige GTIN e duas fontes')
            review = product['revisao']
            require(isinstance(review, dict) and all(review.get(f) for f in ('em','responsavel','metodo','escopo')), f'{key}: revisão ausente')
            date.fromisoformat(review['em'])
            require(not any(p != 'obter_foto_com_uso_liberado' for p in product['pendencias']), f'{key}: pendência comercial impede aprovação')
    unique_index(packages, 'pacotes')
    for package in packages:
        ids = package['produto_ids']
        require(isinstance(ids, list) and len(ids) == len(set(ids)), f'{package["id"]}: seleção duplicada')
        require(all(i in items for i in ids), f'{package["id"]}: produto inexistente')
    return items, cats, src


def csv_text(fields, rows):
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields, delimiter=';', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return '\ufeff' + buffer.getvalue()


def build(root=ROOT, check=False):
    directory = root / 'produtos'
    def read(path):
        return json.loads((directory / path).read_text(encoding='utf-8'))
    catalog, categories, sources = [read(p) for p in ('catalogo.json','categorias.json','fontes.json')]
    packages = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((directory / 'pacotes').glob('*.json'))]
    items, cats, src = validate(catalog, categories, sources, packages)
    fields = ['servos_id','descricao','grupo','marca','conteudo_ml','embalagem','unidade','gtin','foto_url']
    def row(product):
        return dict(zip(fields, [product['id'],product['descricao'],cats[product['categoria_id']]['nome'],product['marca'],product['conteudo_ml'],product['embalagem'],product['unidade_venda'],'|'.join(product['gtins']),product['imagem']['url'] or '']))
    outputs = {}
    approved = [p for p in items.values() if p['status'] == 'aprovado']
    outputs['aprovados.csv'] = csv_text(fields, map(row, approved))
    review_fields = fields + ['status','gtin_candidato','pendencias','fontes']
    outputs['revisao.csv'] = csv_text(review_fields, [dict(row(p),status=p['status'],gtin_candidato='|'.join(c['valor_observado'] for c in p['codigos_candidatos']),pendencias='|'.join(p['pendencias']),fontes='|'.join(src[e['fonte_id']]['url'] for e in p['evidencias'])) for p in items.values()])
    for package in packages:
        require(re.fullmatch(r'[a-z0-9-]+', package['id']), 'id de pacote inseguro')
        outputs[f'pacote-{package["id"]}.csv'] = csv_text(fields, [row(items[i]) for i in package['produto_ids'] if items[i]['status'] == 'aprovado'])
    input_paths = sorted([directory / name for name in ('catalogo.json','categorias.json','fontes.json')] + list((directory / 'pacotes').glob('*.json')))
    manifest = {'schema_version':'1.0.0','catalog_version':catalog['catalog_version'],'total':len(items),'por_status':dict(sorted(Counter(p['status'] for p in items.values()).items())),'imagens_liberadas':sum(p['imagem']['status']=='liberada' for p in items.values()),'candidatos_com_digito_invalido':[{'produto_id':p['id'],'valor_observado':c['valor_observado']} for p in items.values() for c in p['codigos_candidatos'] if not gtin_valid(c['valor_observado'])],'entradas_sha256':{str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths},'sha256':{name:hashlib.sha256(content.encode('utf-8')).hexdigest() for name,content in sorted(outputs.items())}}
    outputs['manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    destination = directory / 'exports'
    if not check:
        destination.mkdir(exist_ok=True)
    for name, content in outputs.items():
        path = destination / name
        if check:
            require(path.exists() and path.read_bytes() == content.encode('utf-8'), f'Exportação desatualizada: {name}')
        else:
            path.write_bytes(content.encode('utf-8'))
    print(f'Catálogo válido: {len(items)} produtos; {len(approved)} aprovados; {manifest["imagens_liberadas"]} fotos liberadas.')
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Valida e confere exportações sem gravar')
    args = parser.parse_args()
    try:
        build(check=args.check)
    except (ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Catálogo inválido: {exc}\n')
