"""Serve the integration-scoped action list through HA's frontend API."""
from pathlib import Path
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from .const import VERSION


async def async_register_editor(hass):
    url = '/grok_connector/actions-editor.js'
    await hass.http.async_register_static_paths([
        StaticPathConfig(url,str(Path(__file__).parent / 'frontend/actions-editor.js'),True)
    ])
    add_extra_js_url(hass,f'{url}?v={VERSION}')
