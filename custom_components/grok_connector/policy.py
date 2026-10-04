"""Explicitly selected entities and administrator-authored HA actions."""
from dataclasses import dataclass
import json
import re
from .const import MAX_ENTITIES

class PolicyError(ValueError):
    """Stable translation key without household data."""

def entity_list(value):
    if not isinstance(value,list) or len(value) > MAX_ENTITIES:
        raise PolicyError('invalid_selection')
    if any(not isinstance(item,str) or len(item) > 255
           or not re.fullmatch(r'[a-z_][a-z0-9_]*\.[a-z0-9_]+',item) for item in value):
        raise PolicyError('invalid_selection')
    return tuple(sorted(set(value)))

@dataclass(frozen=True)
class Action:
    id: str
    name: str
    description: str
    sequence_json: str

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or set(data) != {'id','name','description','sequence'}:
            raise PolicyError('invalid_action')
        identifier,name,description,sequence = (data[key] for key in ('id','name','description','sequence'))
        if (not isinstance(identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',identifier)
                or not isinstance(name,str) or not 1 <= len(name.strip()) <= 80
                or not isinstance(description,str) or len(description) > 500
                or any(ord(c) < 32 for c in name)
                or not isinstance(sequence,list) or not 1 <= len(sequence) <= 100
                or not all(isinstance(step,dict) for step in sequence)):
            raise PolicyError('invalid_action')
        try:
            encoded = json.dumps(sequence,sort_keys=True,ensure_ascii=False,allow_nan=False)
        except (TypeError,ValueError,RecursionError):
            raise PolicyError('invalid_action') from None
        if len(encoded.encode('utf-8')) > 65536:
            raise PolicyError('invalid_action')
        return cls(identifier,name.strip(),description,encoded)

    @property
    def sequence(self):
        return json.loads(self.sequence_json)

    def as_dict(self):
        return {'id':self.id,'name':self.name,'description':self.description,'sequence':self.sequence}

@dataclass(frozen=True)
class Policy:
    readable: tuple[str,...]
    actions: tuple[Action,...] = ()

    @classmethod
    def from_dict(cls,data):
        readable = entity_list(data.get('read_entities',[]))
        actions = data.get('actions',[])
        if not isinstance(actions,list) or len(actions) > 64:
            raise PolicyError('invalid_action')
        parsed = tuple(Action.from_dict(action) for action in actions)
        if len({action.id for action in parsed}) != len(parsed):
            raise PolicyError('invalid_action')
        return cls(readable,parsed)

    def as_dict(self):
        return {'read_entities':list(self.readable),'actions':[action.as_dict() for action in self.actions]}
