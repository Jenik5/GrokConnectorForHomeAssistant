"""Generic MCP tools for selected state and fixed, administrator-authored actions."""
import asyncio
import copy
import json
import secrets
import time
from .const import VERSION
from .i18n import text

PROTOCOLS = ('2024-11-05','2025-03-26','2025-06-18','2025-11-25')
EMPTY_INPUT = {'type':'object','properties':{},'additionalProperties':False}
SESSION_LIFETIME = 1800
MAX_SESSIONS = 128

def content(data,error=False):
    return {'content':[{'type':'text','text':json.dumps(data,ensure_ascii=False)}],'isError':error}

class Gateway:
    def __init__(self,state_reader,action_runner,policy,catalogs,language='en',
                 *,name_reader=None,unit_reader=None,authorized=None,clock=time.monotonic):
        self.state_reader,self.action_runner,self.policy = state_reader,action_runner,policy
        self.catalogs,self.language,self.clock = catalogs,language,clock
        self.name_reader = name_reader or (lambda entity:entity)
        self.unit_reader = unit_reader or (lambda entity:None)
        self.authorized = authorized or (lambda principal:True)
        self.lock,self.replies,self.sessions = asyncio.Lock(),{},{}

    def close_session(self, session):
        self.sessions.pop(session, None)
        self.replies = {key:value for key,value in self.replies.items() if key[1] != session}

    def prune_sessions(self):
        now = self.clock()
        for session, (principal, expires) in list(self.sessions.items()):
            if expires <= now or not self.authorized(principal):
                self.close_session(session)

    def open_session(self, principal):
        self.prune_sessions()
        if not self.authorized(principal):
            raise ValueError('Authorization revoked')
        if len(self.sessions) >= MAX_SESSIONS:
            self.close_session(next(iter(self.sessions)))
        session = secrets.token_urlsafe(32)
        self.sessions[session] = (principal, self.clock()+SESSION_LIFETIME)
        return session

    def session_active(self, session, principal):
        self.prune_sessions()
        if not isinstance(session, str) or session not in self.sessions:
            return False
        owner, _ = self.sessions[session]
        if owner != principal:
            return False
        self.sessions[session] = (owner, self.clock()+SESSION_LIFETIME)
        return True

    def clear(self):
        self.replies.clear()
        self.sessions.clear()

    def status(self):
        entities = []
        for entity in self.policy.readable:
            state = self.state_reader(entity)
            item = {'entity_id':entity,'name':str(self.name_reader(entity))[:255],
                    'state':state if isinstance(state,str) else 'unavailable'}
            unit = self.unit_reader(entity)
            if isinstance(unit,str):
                item['unit'] = unit[:64]
            entities.append(item)
        return {'entities':entities}

    def tools(self):
        tools = [{'name':'entities_status','description':text(self.catalogs,self.language,'tool_status'),
                  'inputSchema':copy.deepcopy(EMPTY_INPUT),
                  'annotations':{'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}}]
        for action in self.policy.actions:
            tools.append({'name':'action_'+action.id,
                'title':action.name,
                'description':text(self.catalogs,self.language,'tool_action').format(name=action.name,description=action.description),
                'inputSchema':copy.deepcopy(EMPTY_INPUT),
                'annotations':{'readOnlyHint':False,'destructiveHint':True,'idempotentHint':False,'openWorldHint':True}})
        return tools

    async def rpc(self,message,principal,*,session=None):
        if (not isinstance(message,dict) or message.get('jsonrpc') != '2.0'
                or not isinstance(message.get('method'),str)
                or ('id' in message and type(message['id']) not in (str,int))):
            return self.error(None,-32600,'Invalid JSON-RPC request')
        if 'id' not in message:
            return None
        request_id,method = message['id'],message['method']
        params = message.get('params',{})
        if not isinstance(params,dict):
            return self.error(request_id,-32602,'Invalid parameters')
        if not self.authorized(principal):
            return self.error(request_id,-32001,'Authorization revoked')
        if session is not None and not self.session_active(session,principal):
            return self.error(request_id,-32000,'MCP session expired')
        if method == 'initialize':
            requested = params.get('protocolVersion')
            result = {'protocolVersion':requested if requested in PROTOCOLS else PROTOCOLS[-1],
                'capabilities':{'tools':{'listChanged':False}},
                'serverInfo':{'name':'Grok Connector','version':VERSION},
                'instructions':text(self.catalogs,self.language,'instructions')}
        elif method == 'ping':
            result = {}
        elif method == 'tools/list':
            result = {'tools':self.tools()}
        elif method == 'tools/call':
            name,arguments = params.get('name'),params.get('arguments',{})
            if set(params)-{'name','arguments','_meta'} or not isinstance(name,str) or arguments != {}:
                return self.error(request_id,-32602,'Invalid tool parameters')
            if name == 'entities_status':
                result = content(self.status())
            else:
                async with self.lock:
                    if not self.authorized(principal):
                        return self.error(request_id,-32001,'Authorization revoked')
                    if session is not None and not self.session_active(session,principal):
                        return self.error(request_id,-32000,'MCP session expired')
                    actions = {'action_'+action.id:action for action in self.policy.actions}
                    if name not in actions:
                        return self.error(request_id,-32602,'Action not permitted')
                    now = self.clock()
                    self.replies = {key:value for key,value in self.replies.items() if value[0] > now}
                    # JSON-RPC IDs identify requests within an MCP session, not
                    # across an OAuth grant. Stateless requests have no reliable
                    # retry identity and must not share a grant-wide cache.
                    key = (principal,session,type(request_id),request_id)
                    if session is not None and key in self.replies:
                        _,previous,cached = self.replies[key]
                        if previous != name:
                            return self.error(request_id,-32602,'Request ID already used for another action')
                        result = copy.deepcopy(cached)
                    else:
                        try:
                            await self.action_runner(actions[name].id)
                        except Exception:
                            result = content({'error':'action_execution_uncertain',
                                'instruction':'Do not retry automatically. Check the state and HA trace.'},True)
                        else:
                            result = content({'result':'action_sequence_finished','physical_effect_confirmed':False})
                        if session is not None and session in self.sessions:
                            if len(self.replies) >= 256:
                                self.replies.pop(next(iter(self.replies)))
                            self.replies[key] = (self.clock()+120,name,copy.deepcopy(result))
        else:
            return self.error(request_id,-32601,'Method not found')
        return {'jsonrpc':'2.0','id':request_id,'result':result}

    @staticmethod
    def error(request_id,code,message):
        return {'jsonrpc':'2.0','id':request_id,'error':{'code':code,'message':message}}
