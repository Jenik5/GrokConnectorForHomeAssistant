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

class ActionListSelector(selector.ObjectSelector):
    """Native object-list validation with internal, non-editable tool IDs."""
    # Keep the form functional when an older page has not loaded our styling.
    selector_type = 'object'

    def __call__(self,value):
        if not isinstance(value,list) or len(value) > 64:
            raise vol.Invalid('invalid_action')
        if any(not isinstance(item,dict) for item in value):
            raise vol.Invalid('invalid_action')
        # HA's form retains extra data on an edited object. IDs are not fields
        # users can edit; validate all visible fields through the native selector.
        super().__call__([{key:item[key] for key in item if key != 'id'} for item in value])
        return value

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
        errors = {}
        shown = self._draft.get('actions',[])
        if user_input is not None:
            shown = user_input.get('actions',[])
            try:
                if not isinstance(shown,list) or len(shown) > 64:
                    raise PolicyError('invalid_action')
                known_ids = {item['id'] for item in self._draft.get('actions',[])}
                actions = []
                for item in shown:
                    if not isinstance(item,dict) or set(item) - {'id','name','description','sequence'}:
                        raise PolicyError('invalid_action')
                    if 'id' in item and (not isinstance(item['id'],str) or item['id'] not in known_ids):
                        raise PolicyError('invalid_action')
                    action = Action.from_dict({**item,'id':item.get('id',uuid.uuid4().hex),
                                               'description':item.get('description','')})
                    actions.append(action.as_dict())
                candidate = {**self._draft,'actions':actions}
                policy = Policy.from_dict(candidate)
                for action in policy.actions:
                    await async_validate_actions_config(self.hass,cv.SCRIPT_SCHEMA(action.sequence))
            except (PolicyError,vol.Invalid):
                errors['base'] = 'invalid_action'
            else:
                self._draft = candidate
                return self.async_create_entry(title='',data=copy.deepcopy(candidate))
        return self.async_show_form(step_id='actions',errors=errors,data_schema=vol.Schema({
            vol.Required('actions',default=shown):ActionListSelector(selector.ObjectSelectorConfig(
                multiple=True,label_field='name',description_field='description',translation_key='grok_actions',
                fields={
                    'name':{'required':True,'selector':selector.TextSelector()},
                    'description':{'selector':selector.TextSelector()},
                    'sequence':{'required':True,'selector':selector.ActionSelector()},
                })),
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
