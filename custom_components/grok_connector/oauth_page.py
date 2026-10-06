# custom_components/grok_connector/oauth_page.py
"""No-script localized consent document with per-transaction secure cookies."""
import base64
import hashlib
import html
import re
from pathlib import Path

from .const import OAUTH_PATH
from .i18n import browser_language, text

# Brand icon inlined: the page CSP forbids scripts and external images, inline SVG needs neither.
LOGO = (Path(__file__).parent / 'brand/icon.svg').read_text(encoding='utf-8')
# Light by default, dark via the browser preference; HA blue is the accent colour.
STYLE = '''
:root{color-scheme:light dark;--bg:#f4f6f8;--card:#fff;--fg:#1c2733;--muted:#5f6b7a;--line:#dbe1e8;--accent:#03a9f4;--accent-fg:#fff;--soft:#e8f6fd}
@media(prefers-color-scheme:dark){:root{--bg:#111518;--card:#1c2228;--fg:#e6ebf0;--muted:#9aa6b4;--line:#333d47;--accent:#18bcf2;--accent-fg:#06202b;--soft:#15303d}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{width:100%;max-width:440px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:32px 28px;box-shadow:0 4px 24px rgba(0,0,0,.08)}
.logo{text-align:center}.logo svg{width:84px;height:84px}
h1{font-size:1.35rem;line-height:1.3;text-align:center;margin:12px 0 16px}
.badge{background:var(--soft);border-radius:10px;padding:10px 14px;font-size:.92rem;margin:0 0 14px}
.muted{color:var(--muted);font-size:.9rem;margin:0 0 14px}
.muted strong{display:block;color:var(--fg);font:.85rem ui-monospace,monospace;word-break:break-all;margin-top:2px}
label{display:block;font-weight:600;margin:18px 0 6px}
input{width:100%;padding:12px 14px;font:1.1rem ui-monospace,monospace;letter-spacing:.06em;color:var(--fg);background:var(--bg);border:2px solid var(--line);border-radius:10px}
input:focus{outline:none;border-color:var(--accent)}
button{width:100%;margin-top:16px;padding:13px;font-family:inherit;font-weight:600;font-size:1rem;color:var(--accent-fg);background:var(--accent);border:0;border-radius:10px;cursor:pointer}
button:hover{filter:brightness(1.08)}button:focus-visible{outline:3px solid var(--fg);outline-offset:2px}
footer{margin-top:20px;text-align:center;color:var(--muted);font-size:.8rem}
'''
# CSP source allowing exactly this stylesheet (no 'unsafe-inline'); the page CSP is otherwise default-src 'none'.
STYLE_SOURCE = "'sha256-" + base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode() + "'"


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
<meta name="referrer" content="same-origin"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><title>{t('page_title')}</title>
<style>{STYLE}</style></head><body><main><div class="logo">{LOGO}</div><h1>{t('page_title')}</h1>
<p class="badge">{html.escape(count)}</p>
<p class="muted">{t('callback')}<strong>{html.escape(callback)}</strong></p>
<p class="muted">{t('pair_help')}</p><form method="post" action="{OAUTH_PATH}/authorize">
<input type="hidden" name="transaction" value="{html.escape(transaction)}">
<label for="pairing_secret">{t('pair_label')}</label>
<input id="pairing_secret" type="password" name="pairing_secret" required autocomplete="off" maxlength="64" autofocus>
<button type="submit">{t('approve')}</button></form><footer>{t('community')}</footer></main></body></html>'''
    return page
