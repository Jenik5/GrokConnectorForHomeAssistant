"""Native selectors for any entity and administrator-authored HA action sequences."""
import copy
import uuid
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.script import async_validate_actions_config
from .const import DOMAIN,MCP_PATH
from .i18n import load_catalogs
from .policy import Action,Policy,PolicyError,entity_list
from .security import public_base

def language_selector(catalogs):
    return selector.SelectSelector(selector.SelectSelectorConfig(options=[
        {'value':language,'label':catalogs[language]['language_name']}
        for language in ['en',*sorted(set(catalogs)-{'en'})]]))

class EntitySteps:
    async def async_step_entities(self,user_input=None):
        errors = {}
        if user_input is not None:
            try:
                selected = entity_list(user_input.get('read_entities',[]))
            except PolicyError:
                errors['base'] = 'invalid_selection'
            else:
                self._draft['read_entities'] = list(selected)
                Policy.from_dict(self._draft)
                return self.async_create_entry(title='Grok Connector' if isinstance(self,config_entries.ConfigFlow) else '',
                                               data=copy.deepcopy(self._draft))
        return self.async_show_form(step_id='entities',errors=errors,data_schema=vol.Schema({
            vol.Required('read_entities',default=self._draft.get('read_entities',[])):
                selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
        }))

class GrokConfigFlow(EntitySteps,config_entries.ConfigFlow,domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self,user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason='already_configured')
        errors = {}
        catalogs = await self.hass.async_add_executor_job(load_catalogs)
        if user_input is not None:
            try:
                base = public_base(user_input['public_url'])
                language = user_input['language']
                if language not in catalogs:
                    raise ValueError()
            except (ValueError,KeyError):
                errors['base'] = 'invalid_url'
            else:
                self._draft = {'public_url':base,'language':language,'actions':[]}
                return await self.async_step_entities()
        try:
            default = get_url(self.hass,require_cloud=True)
        except NoURLAvailableError:
            default = ''
        language = self.hass.config.language.replace('_','-').split('-')[0]
        return self.async_show_form(step_id='user',errors=errors,data_schema=vol.Schema({
            vol.Required('public_url',default=default):str,
            vol.Required('language',default=language if language in catalogs else 'en'):language_selector(catalogs),
        }))
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GrokOptionsFlow()

class GrokOptionsFlow(EntitySteps,config_entries.OptionsFlow):
    async def async_step_init(self,user_input=None):
        if DOMAIN not in self.hass.data:
            return self.async_abort(reason='not_loaded')
        self._draft = copy.deepcopy(dict(self.config_entry.options or self.config_entry.data))
        return self.async_show_menu(step_id='init',menu_options=['entities','actions','language','pair','revoke'])
    async def async_step_actions(self,user_input=None):
        return self.async_show_menu(step_id='actions',menu_options=['add_action','edit_action','delete_action'])
    async def async_step_add_action(self,user_input=None):
        if len(self._draft.get('actions',[])) >= 64:
            return self.async_abort(reason='too_many_actions')
        self._action_id = uuid.uuid4().hex
        return await self.async_step_action()
    async def _select_action(self,step_id,user_input=None):
        actions = self._draft.get('actions',[])
        if not actions:
            return self.async_abort(reason='no_actions')
        if user_input is not None and user_input.get('action_id') in {action['id'] for action in actions}:
            self._action_id = user_input['action_id']
            return await (self.async_step_action() if step_id == 'edit_action' else self.async_step_confirm_delete())
        return self.async_show_form(step_id=step_id,data_schema=vol.Schema({
            vol.Required('action_id'):selector.SelectSelector(selector.SelectSelectorConfig(
                options=[{'value':action['id'],'label':action['name']} for action in actions])),
        }))
    async def async_step_edit_action(self,user_input=None):
        return await self._select_action('edit_action',user_input)
    async def async_step_delete_action(self,user_input=None):
        return await self._select_action('delete_action',user_input)
    async def async_step_confirm_delete(self,user_input=None):
        if user_input is not None:
            self._draft['actions'] = [action for action in self._draft['actions'] if action['id'] != self._action_id]
            return self.async_create_entry(title='',data=copy.deepcopy(self._draft))
        name = next(action['name'] for action in self._draft['actions'] if action['id'] == self._action_id)
        return self.async_show_form(step_id='confirm_delete',data_schema=vol.Schema({}),description_placeholders={'name':name})
    async def async_step_action(self,user_input=None):
        existing = next((action for action in self._draft.get('actions',[]) if action['id'] == self._action_id),{})
        errors = {}
        if user_input is not None:
            try:
                action = Action.from_dict({'id':self._action_id,'name':user_input.get('name'),
                    'description':user_input.get('description',''),'sequence':user_input.get('sequence')})
                await async_validate_actions_config(self.hass,cv.SCRIPT_SCHEMA(action.sequence))
            except (PolicyError,vol.Invalid):
                errors['base'] = 'invalid_action'
            else:
                self._draft['actions'] = [item for item in self._draft.get('actions',[]) if item['id'] != action.id]
                self._draft['actions'].append(action.as_dict())
                return self.async_create_entry(title='',data=copy.deepcopy(self._draft))
        return self.async_show_form(step_id='action',errors=errors,data_schema=vol.Schema({
            vol.Required('name',default=existing.get('name','')):str,
            vol.Optional('description',default=existing.get('description','')):str,
            vol.Required('sequence',default=existing.get('sequence',[])):selector.ActionSelector(),
        }))
    async def async_step_language(self,user_input=None):
        runtime = self.hass.data.get(DOMAIN)
        if not runtime:
            return self.async_abort(reason='not_loaded')
        if user_input is not None and user_input.get('language') in runtime.catalogs:
            self._draft['language'] = user_input['language']
            return self.async_create_entry(title='',data=copy.deepcopy(self._draft))
        return self.async_show_form(step_id='language',data_schema=vol.Schema({
            vol.Required('language',default=self._draft.get('language','en')):language_selector(runtime.catalogs),
        }))
    async def async_step_pair(self,user_input=None):
        runtime = self.hass.data.get(DOMAIN)
        if not runtime or not getattr(runtime,'accepting',True):
            return self.async_abort(reason='not_loaded')
        if user_input is not None:
            return self.async_create_entry(title='',data=copy.deepcopy(self._draft))
        if not hasattr(self,'_pairing_secret'):
            self._pairing_secret = runtime.pair()
        return self.async_show_form(step_id='pair',data_schema=vol.Schema({}),description_placeholders={
            'pairing_secret':self._pairing_secret,'mcp_url':runtime.authority.base_url+MCP_PATH})
    async def async_step_revoke(self,user_input=None):
        runtime = self.hass.data.get(DOMAIN)
        if not runtime:
            return self.async_abort(reason='not_loaded')
        if user_input is not None:
            await runtime.revoke()
            return self.async_create_entry(title='',data=copy.deepcopy(self._draft))
        return self.async_show_form(step_id='revoke',data_schema=vol.Schema({}))
