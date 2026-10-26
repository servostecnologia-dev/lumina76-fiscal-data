import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalog', ROOT / 'scripts/build_product_catalog.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.docs = [json.loads((ROOT / 'produtos' / name).read_text()) for name in ('catalogo.json','categorias.json','fontes.json')]
        self.packages = [json.loads(p.read_text()) for p in (ROOT / 'produtos/pacotes').glob('*.json')]

    def validate(self):
        return module.validate(*self.docs, self.packages)

    def test_gtin_formats_and_zeroes(self):
        for code in ('7894900010015','78936683','07894900010015','036000291452'):
            self.assertTrue(module.gtin_valid(code), code)
        for code in ('7894900010016',7894900010015,'00000000','７８９４９０００１００１５','789490001001'):
            self.assertFalse(module.gtin_valid(code), code)

    def test_actual_catalog_and_reproducible_exports(self):
        self.validate()
        outputs = module.build(check=True)
        self.assertEqual(outputs, module.build(check=True))
        self.assertNotIn('SVP-000001', outputs['aprovados.csv'])
        self.assertIn('SVP-000003', outputs['aprovados.csv'])

    def test_duplicate_gtin_with_padding(self):
        products = self.docs[0]['produtos']
        duplicate = copy.deepcopy(products[2])
        duplicate['id'] = 'SVP-999999'
        duplicate['gtins'] = ['07894900010015']
        products.append(duplicate)
        with self.assertRaisesRegex(ValueError, 'duplicado'):
            self.validate()

    def test_approval_without_crosscheck(self):
        product = self.docs[0]['produtos'][2]
        product['evidencias'] = product['evidencias'][:1]
        with self.assertRaises(ValueError):
            self.validate()

    def test_pending_commercial_data_blocks_approval(self):
        self.docs[0]['produtos'][2]['pendencias'].append('confirmar_gtin_unitario')
        with self.assertRaisesRegex(ValueError, 'pendência comercial'):
            self.validate()

    def test_unknown_image_usage_blocks_distribution(self):
        self.docs[0]['produtos'][2]['imagem'] = {'status':'liberada','url':'https://example.com/photo.jpg','fonte_id':'bahiafarma-coca350','condicao_uso':None}
        with self.assertRaisesRegex(ValueError, 'condição de uso'):
            self.validate()

    def test_category_cycle(self):
        self.docs[1]['categorias'][0]['pai_id'] = 'cervejas'
        with self.assertRaisesRegex(ValueError, 'ciclo'):
            self.validate()

    def test_package_missing_product(self):
        self.packages[0]['produto_ids'].append('SVP-999999')
        with self.assertRaisesRegex(ValueError, 'inexistente'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
