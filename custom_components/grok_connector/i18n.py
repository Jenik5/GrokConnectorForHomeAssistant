"""Extend translations with one HA translation and one public-page locale file."""
import json
from pathlib import Path


def load_catalogs():
    return {path.stem:json.loads(path.read_text(encoding='utf-8'))
            for path in sorted((Path(__file__).parent/'locales').glob('*.json'))}


def choose_language(value, catalogs, default='en'):
    language = str(value or '').replace('_', '-').split('-')[0].lower()
    return language if language in catalogs else default if default in catalogs else 'en'


def browser_language(header, catalogs, default='en'):
    # Respect explicit language weights, including q=0 exclusion.
    choices = []
    for index, item in enumerate(str(header or '')[:1024].split(',')):
        parts = item.strip().split(';')
        try:
            quality = next((float(p.strip()[2:]) for p in parts[1:] if p.strip().startswith('q=')), 1.0)
        except ValueError:
            continue
        language = parts[0].replace('_', '-').split('-')[0].lower()
        if language in catalogs and 0 < quality <= 1:
            choices.append((quality, -index, language))
    return max(choices)[2] if choices else choose_language(default, catalogs)


def text(catalogs, language, key):
    return catalogs.get(language, {}).get(key, catalogs['en'][key])
