import json
from email.message import Message
import unittest
from unittest.mock import MagicMock, patch
import core
import product_source


class ProductSourceTests(unittest.TestCase):
    def extract(self, value):
        return product_source.single_product([json.dumps(value)])

    def test_product_graph_extracts_explicit_features_and_preserves_numbers(self):
        result = self.extract({'@graph': [{'@type': 'WebPage'}, {
            '@type': ['Thing', 'Product'], 'name': 'Organizador &amp; base',
            'description': '<p>Possui três divisórias.</p><script>compre agora</script>',
            'material': 'Madeira', 'color': 'Verde',
            'additionalProperty': [{'name': 'Temperatura mínima', 'value': -5, 'unitText': '°C'},
                                   {'name': 'Peso', 'value': 1.5, 'unitText': 'kg'}]}]})
        self.assertEqual(result['name'], 'Organizador & base')
        self.assertIn('Possui três divisórias.', result['description'])
        self.assertIn('Material: Madeira', result['description'])
        self.assertIn('Temperatura mínima: -5 °C', result['description'])
        self.assertIn('Peso: 1.5 kg', result['description'])
        self.assertNotIn('compre agora', result['description'])

    def test_main_entity_ignores_recommendations_prices_and_ratings(self):
        product = {'@type': 'https://schema.org/Product', 'name': 'Produto principal',
                   'material': 'Aço', 'offers': {'price': 12}, 'aggregateRating': {'ratingValue': 5},
                   'isRelatedTo': {'@type': 'Product', 'name': 'Outro produto', 'material': 'Plástico'}}
        result = self.extract({'@type': 'WebPage', 'mainEntity': product})
        self.assertEqual(result['name'], 'Produto principal')
        self.assertEqual(result['description'], 'Material: Aço')

    def test_ambiguous_products_do_not_mix_features(self):
        self.assertEqual(self.extract([{'@type': 'Product', 'name': 'A'}, {'@type': 'Product', 'name': 'B'}]), {})
        self.assertEqual(self.extract({'@type': 'ItemList', 'itemListElement': [{'@type': 'Product', 'name': 'A'}]}), {})

    def test_malformed_deep_and_non_product_json_fall_back(self):
        for block in ['invalid', '[]', 'null', '{"@type":"Product","name":{}}', '[' * 2000 + ']' * 2000]:
            self.assertEqual(product_source.single_product([block]), {})
        node = {'@type': 'Product', 'name': 'Nested'}
        for _ in range(15):
            node = {'mainEntity': node}
        self.assertEqual(self.extract(node), {})

    def test_optional_fields_are_bounded_and_do_not_stringify_objects(self):
        result = self.extract({'@type': 'Product', 'name': 'A' * 200, 'description': 'D' * 900,
                               'material': {'name': 'unknown'}, 'size': ['A', 'B'],
                               'additionalProperty': {'name': 'Medida', 'value': {'value': 'inventado'}}})
        self.assertEqual(len(result['name']), 140)
        self.assertEqual(len(result['description']), 650)
        self.assertNotIn('inventado', result['description'])
        result = self.extract({'@type': 'Product', 'name': 'A', 'additionalProperty': {'name': 'Peso', 'value': float('nan')}})
        self.assertEqual(result['description'], '')

    def test_parser_only_collects_bounded_json_ld_and_never_executes_scripts(self):
        parser = core.MetadataParser()
        parser.feed('<script>alert(1)</script>' + '<script type="application/ld+json">' + 'x' * 70000 + '</script>')
        self.assertEqual(len(parser.json_blocks), 1)
        self.assertEqual(len(parser.json_blocks[0]), 64000)
        parser.feed('<script type="application/ld+json">{}</script>' * 30)
        self.assertEqual(len(parser.json_blocks), 20)

    def test_import_prefers_single_product_and_keeps_affiliate_request(self):
        url = 'https://example.com/p?ref=meu-id&origem=video'
        headers = Message(); headers['Content-Type'] = 'text/html; charset=utf-8'
        response = MagicMock(); response.headers = headers
        response.read.return_value = ('<title>Loja</title><script type="application/ld+json">' +
            json.dumps({'@type': 'Product', 'name': 'Organizador', 'material': 'Madeira'}) + '</script>').encode()
        opener = MagicMock(); opener.open.return_value.__enter__.return_value = response
        with patch('core.public_url', return_value=url), patch('core.build_opener', return_value=opener):
            result = core.import_product(url)
        self.assertEqual(opener.open.call_args.args[0].full_url, url)
        self.assertEqual(result['source'], 'schema.org/Product')
        self.assertEqual(result['description'], 'Material: Madeira')
        self.assertNotIn('url', result)

    def test_product_without_supported_json_uses_html_and_does_not_infer_commission(self):
        headers = Message(); headers['Content-Type'] = 'text/html'
        response = MagicMock(); response.headers = headers
        response.read.return_value = b'<title>Produto HTML</title><meta name="description" content="Dados da loja.">'
        opener = MagicMock(); opener.open.return_value.__enter__.return_value = response
        with patch('core.public_url', return_value='https://example.com'), patch('core.build_opener', return_value=opener):
            result = core.import_product('https://example.com')
        self.assertEqual(result['source'], 'metadados HTML')
        self.assertEqual(result['description'], 'Dados da loja.')
        self.assertNotIn('commission', result)
