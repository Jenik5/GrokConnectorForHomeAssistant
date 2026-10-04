"""Translation parity, extensibility and anonymous OAuth page rendering."""
import json
from string import Formatter
import types
import unittest
from test_gateway import ROOT, i18n, package
import importlib

page = importlib.import_module(package.__name__ + '.oauth_page')


def flattened(value, prefix=''):
    if isinstance(value, dict):
        return {key: child for name, entry in value.items()
                for key, child in flattened(entry, prefix + '/' + name).items()}
    return {prefix: value}


def placeholders(value):
    return {field for _, field, _, _ in Formatter().parse(value) if field is not None}


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.catalogs = i18n.load_catalogs()

    def test_all_five_languages_have_the_same_keys_and_placeholders(self):
        self.assertEqual(set(self.catalogs), {'en', 'cs', 'de', 'pl', 'sk'})
        english = flattened(json.loads((ROOT / 'strings.json').read_text(encoding='utf-8')))
        for language in self.catalogs:
            with self.subTest(language=language):
                translation = flattened(json.loads((ROOT / 'translations' / (language + '.json')).read_text(encoding='utf-8')))
                self.assertEqual(set(translation), set(english))
                self.assertEqual(set(self.catalogs[language]), set(self.catalogs['en']))
                for key in english:
                    self.assertEqual(placeholders(translation[key]), placeholders(english[key]))
                for key in self.catalogs['en']:
                    self.assertEqual(placeholders(self.catalogs[language][key]), placeholders(self.catalogs['en'][key]))
        self.assertEqual(json.loads((ROOT / 'strings.json').read_text(encoding='utf-8')),
                         json.loads((ROOT / 'translations/en.json').read_text(encoding='utf-8')))

    def test_regional_fallback_and_browser_language_preferences(self):
        self.assertEqual(i18n.choose_language('cs-CZ', self.catalogs), 'cs')
        self.assertEqual(i18n.choose_language('fr', self.catalogs), 'en')
        self.assertEqual(i18n.browser_language('de;q=0,pl-PL;q=0.8,cs;q=0.9', self.catalogs), 'cs')
        self.assertEqual(i18n.browser_language('de;q=bad,sk;q=0.5', self.catalogs), 'sk')
        self.assertEqual(i18n.text(self.catalogs, 'fr', 'tool_status'), self.catalogs['en']['tool_status'])
        extended = {**self.catalogs, 'fr': {'language_name': 'Français'}}
        self.assertEqual(i18n.choose_language('fr-FR', extended), 'fr')
        self.assertEqual(i18n.text(extended, 'fr', 'tool_status'), self.catalogs['en']['tool_status'])

    def test_public_page_escapes_values_and_discloses_counts_only(self):
        runtime = types.SimpleNamespace(catalogs=self.catalogs, language='cs',
            policy=types.SimpleNamespace(readable=['sensor.private_house'], actions=['private-action']))
        rendered = page.render_authorization(runtime,
            types.SimpleNamespace(headers={'Accept-Language': 'de-DE'}),
            'https://grok.com/callback?value=<script>', '<private-transaction>')
        self.assertNotIn('sensor.private_house', rendered)
        self.assertNotIn('private-action', rendered)
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<private-transaction>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('<html lang="de">', rendered)
        self.assertIn('name="referrer" content="same-origin"', rendered)

    def test_parallel_transactions_have_independent_cookie_names(self):
        self.assertNotEqual(page.transaction_cookie_name('a' * 43), page.transaction_cookie_name('b' * 43))
        self.assertNotIn('a' * 43, page.transaction_cookie_name('a' * 43))
        self.assertEqual(page.transaction_cookie_name('invalid\ntransaction'), 'grok_connector_transaction_invalid')
