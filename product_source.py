"""Read a single Product from embedded JSON-LD without resolving remote contexts."""
import json
import math
from html.parser import HTMLParser


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif tag in ('br', 'p', 'li', 'div'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def text(value):
    if not isinstance(value, str):
        return ''
    parser = PlainText()
    parser.feed(value[:20_000])
    return ' '.join(''.join(parser.parts).split())


def single_product(blocks):
    """Ignore recommendations/variants; ambiguous product lists use HTML fallback."""
    candidates = []
    for block in blocks[:20]:
        try:
            document = json.loads(block)
        except (ValueError, RecursionError):
            continue
        pending = [(document, 0)]
        while pending:
            node, depth = pending.pop()
            if depth > 12:
                continue
            if isinstance(node, list):
                pending.extend((item, depth + 1) for item in node[:100])
            elif isinstance(node, dict):
                types = node.get('@type', [])
                types = [types] if isinstance(types, str) else types
                if isinstance(types, list) and any(t in ('Product', 'https://schema.org/Product', 'http://schema.org/Product') for t in types if isinstance(t, str)):
                    if node not in candidates:
                        candidates.append(node)
                    if len(candidates) > 1:
                        return {}
                else:
                    for key in ('@graph', 'mainEntity'):
                        if key in node:
                            pending.append((node[key], depth + 1))
    if len(candidates) != 1:
        return {}
    product = candidates[0]
    name = text(product.get('name'))[:140]
    if not name:
        return {}
    description = text(product.get('description'))[:650]
    facts = []
    for key, label in [('material', 'Material'), ('color', 'Cor'), ('size', 'Tamanho'), ('model', 'Modelo')]:
        value = text(product.get(key))
        if value and len(value) <= 160:
            facts.append(f'{label}: {value}')
    properties = product.get('additionalProperty', [])
    if isinstance(properties, dict):
        properties = [properties]
    if isinstance(properties, list):
        for prop in properties[:12]:
            if not isinstance(prop, dict):
                continue
            label, value, unit = text(prop.get('name')), prop.get('value'), text(prop.get('unitText'))
            if type(value) is float and not math.isfinite(value):
                continue
            if type(value) in (int, float):
                value = str(value)
            value = text(value)
            fact = f'{label}: {value}' + (f' {unit}' if unit else '')
            if label and value and len(fact) <= 220:
                facts.append(fact)
    for fact in dict.fromkeys(facts):
        if fact.casefold() in description.casefold():
            continue
        candidate = description + ('\n' if description else '') + fact
        if len(candidate) <= 650:
            description = candidate
    return {'name': name, 'description': description}
