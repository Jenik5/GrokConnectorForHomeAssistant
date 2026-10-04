"""Counts only; never export credentials or household entity data."""
from .const import DOMAIN, VERSION


async def async_get_config_entry_diagnostics(hass, entry):
    runtime = hass.data.get(DOMAIN)
    if not runtime:
        return {'version':VERSION,'loaded':False}
    return {'version':VERSION,'loaded':True,'read_entity_count':len(runtime.policy.readable),
            'action_count':len(runtime.policy.actions),
            'grant_count':len(runtime.authority.grants),'language':runtime.language}
