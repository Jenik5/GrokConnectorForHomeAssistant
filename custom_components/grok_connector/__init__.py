"""Independent HA runtime for selected entities and configured actions."""
import asyncio
import copy
import time

from homeassistant.core import Context
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import Script, async_validate_actions_config
from homeassistant.helpers.storage import Store

from .const import DOMAIN, VERSION
from .diagnostics import emit
from .gateway import Gateway
from .i18n import choose_language, load_catalogs
from .policy import Policy
from .security import OAuthAuthority


class Runtime:
    def __init__(self, hass, entry, store, saved, catalogs):
        self.hass, self.store, self.catalogs = hass, store, catalogs
        self.active, self.token_lock, self.limits = True, asyncio.Lock(), {}
        self.accepting = True
        self.configuration_lock = asyncio.Lock()
        self.authority = OAuthAuthority(entry.data['public_url'], saved)
        settings = entry.options or entry.data
        self.policy = Policy.from_dict(settings)
        self.language = choose_language(settings.get('language',hass.config.language),catalogs)
        self.scripts = {}

        def read_state(entity):
            state = hass.states.get(entity)
            return state.state if state else None

        def read_attribute(entity, attribute):
            state = hass.states.get(entity)
            return state.attributes.get(attribute) if state else None

        async def run_action(action_id):
            await self.scripts[action_id].async_run(context=Context())

        self.gateway = Gateway(read_state,run_action,self.policy,catalogs,self.language,
            name_reader=lambda entity:read_attribute(entity,'friendly_name') or entity,
            unit_reader=lambda entity:read_attribute(entity,'unit_of_measurement'),
            authorized=self.principal_active)

    async def make_scripts(self, policy):
        # Validate device actions and nested conditions with HA before creating any
        # Script objects. Keep the user's JSON configuration in the config entry.
        validated = [(action, await async_validate_actions_config(
            self.hass, cv.SCRIPT_SCHEMA(action.sequence))) for action in policy.actions]
        scripts = {}
        try:
            for action, sequence in validated:
                scripts[action.id] = Script(self.hass,sequence,action.name,DOMAIN,
                                            script_mode='single')
        except Exception:
            await asyncio.gather(*(script.async_unload() for script in scripts.values()))
            raise
        return scripts

    async def stop_actions(self):
        await asyncio.gather(*(script.async_stop() for script in self.scripts.values()))

    def principal_active(self, principal):
        grant = self.authority.grants.get(principal)
        now = self.authority.clock()
        return bool(self.active and self.accepting and grant and grant['access_expires'] > now
                    and grant['refresh_expires'] > now and grant.get('resource') == self.authority.resource)

    async def save(self):
        await self.store.async_save(copy.deepcopy(self.authority.snapshot()))

    async def revoke(self):
        async with self.configuration_lock:
            self.accepting = False
            try:
                async with self.token_lock:
                    self.authority.revoke_access()
                    await self.save()
                await self.stop_actions()
                async with self.gateway.lock:
                    self.gateway.replies.clear()
                emit('admin','revoked',grant_count=0)
            finally:
                self.accepting = self.active

    async def apply_options(self, entry):
        async with self.configuration_lock:
            await self._apply_options(entry)

    async def _apply_options(self, entry):
        settings = entry.options or entry.data
        policy = Policy.from_dict(settings)
        language = choose_language(settings.get('language',self.hass.config.language),self.catalogs)
        if policy != self.policy:
            scripts = await self.make_scripts(policy)
            # Consent cannot start or finish against the old policy during the
            # awaited persistence/Script cleanup before replacement.
            self.accepting = False
            adopted = False
            try:
                async with self.token_lock:
                    self.authority.revoke_access()
                    await self.save()
                await asyncio.gather(*(script.async_unload() for script in self.scripts.values()))
                async with self.gateway.lock:
                    self.policy, self.gateway.policy = policy, policy
                    self.scripts = scripts
                    adopted = True
                    self.gateway.replies.clear()
                    emit('admin','revoked',grant_count=0)
            finally:
                if not adopted:
                    await asyncio.gather(*(script.async_unload() for script in scripts.values()))
                self.accepting = self.active
        self.language = self.gateway.language = language

    async def stop(self):
        self.active = self.accepting = False
        async with self.configuration_lock:
            await asyncio.gather(*(script.async_unload() for script in self.scripts.values()))
            async with self.gateway.lock:
                self.gateway.replies.clear()

    def pair(self):
        if not self.active or not self.accepting:
            raise ValueError('Connector is not accepting authorization')
        secret = self.authority.pair()
        emit('admin','pair_created',pending_count=len(self.authority.pending),
             clients_count=len(self.authority.clients))
        return secret

    def rate_allowed(self, category, limit, window=60):
        now = time.monotonic()
        bucket = [t for t in self.limits.get(category,[]) if t > now-window]
        self.limits[category] = bucket
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


async def async_setup(hass, config):
    from .http import register_views
    from .frontend import async_register_editor
    await async_register_editor(hass)
    register_views(hass)
    return True


async def async_setup_entry(hass, entry):
    catalogs = await hass.async_add_executor_job(load_catalogs)
    store = Store(hass,1,DOMAIN,private=True)
    runtime = Runtime(hass,entry,store,await store.async_load(),catalogs)
    runtime.scripts = await runtime.make_scripts(runtime.policy)
    hass.data[DOMAIN] = runtime
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    emit('setup','loaded',warning=True,version=VERSION,grant_count=len(runtime.authority.grants))
    return True


async def async_update_options(hass, entry):
    if runtime := hass.data.get(DOMAIN):
        await runtime.apply_options(entry)


async def async_unload_entry(hass, entry):
    if runtime := hass.data.get(DOMAIN):
        await runtime.stop()
        hass.data.pop(DOMAIN,None)
    return True


async def async_remove_entry(hass, entry):
    await Store(hass,1,DOMAIN,private=True).async_remove()
