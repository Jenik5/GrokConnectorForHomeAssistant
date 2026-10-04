"""No-script localized consent document with per-transaction secure cookies."""
import hashlib
import html
import re

from .const import OAUTH_PATH
from .i18n import browser_language, text


def transaction_cookie_name(transaction):
    if not isinstance(transaction,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',transaction):
        return 'grok_connector_transaction_invalid'
    return 'grok_connector_transaction_' + hashlib.sha256(transaction.encode('ascii')).hexdigest()[:16]


def render_authorization(runtime, request, callback, transaction):
    language = browser_language(request.headers.get('Accept-Language'),runtime.catalogs,runtime.language)
    def t(key):
        return html.escape(text(runtime.catalogs,language,key))
    count = text(runtime.catalogs,language,'permissions').format(
        read_count=len(runtime.policy.readable),control_count=len(runtime.policy.actions))
    # Do not publish the home's entity IDs, names or states on an anonymous page.
    page = f'''<!doctype html><html lang="{language}"><head><meta charset="utf-8">
<meta name="referrer" content="same-origin"><meta name="viewport" content="width=device-width">
<title>{t('page_title')}</title></head><body><main><h1>{t('page_title')}</h1>
<p>{html.escape(count)}</p><p>{t('callback')} <strong>{html.escape(callback)}</strong></p>
<p>{t('pair_help')}</p><form method="post" action="{OAUTH_PATH}/authorize">
<input type="hidden" name="transaction" value="{html.escape(transaction)}">
<label>{t('pair_label')} <input type="password" name="pairing_secret" required autocomplete="off" maxlength="64"></label>
<button type="submit">{t('approve')}</button></form><p>{t('community')}</p></main></body></html>'''
    return page
