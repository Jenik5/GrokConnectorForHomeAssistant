"""Bounded diagnostics containing only fixed categories, flags and counts.

Never log request bodies, raw headers, URLs, credentials, credential hashes,
client identifiers or exception messages. Flow IDs are unrelated random IDs.
"""

from collections import deque
import json
import logging
import re
import time

_LOGGER = logging.getLogger(__name__)
_WINDOW = deque()
_LIMIT = 180
_STAGES = {"setup", "admin", "resource_metadata", "server_metadata", "registration",
           "authorize_get", "authorize_post", "token", "mcp"}
_OUTCOMES = {"request", "response", "rejected", "failed", "cancelled", "loaded",
             "pair_created", "revoked", "origin_denied", "rate_limited",
             "registered", "invalid_registration", "form_created", "invalid_authorization",
             "cookie_missing", "cookie_mismatch", "transaction_missing", "pairing_rejected",
             "redirect_issued", "token_rejected", "token_issued", "bearer_rejected"}
_FLAGS = {"origin_allowed", "host_matches", "cookie_header", "cookie_present", "cookie_matches",
          "transaction_present", "transaction_known", "transaction_live", "pairing_present",
          "pairing_live", "pairing_matches", "pair_code_supplied", "client_known", "client_live",
          "redirect_matches", "resource_supplied", "resource_matches", "state_supplied",
          "state_valid", "pkce_s256", "challenge_valid", "scope_matches", "response_type_code",
          "authorization_present", "bearer_valid", "code_present", "code_known", "code_live",
          "verifier_valid", "code_client_matches", "code_redirect_matches", "pkce_matches",
          "refresh_present", "client_secret_supplied", "accepts_json", "protocol_supported"}
_COUNTS = {"status", "pending_count", "clients_count", "grant_count", "failed_pairings",
           "cookie_name_count", "redirect_count"}
_CATEGORIES = {
    "origin": {"missing", "null", "gateway", "grok", "other"},
    "scheme": {"http", "https", "other"},
    "method": {"GET", "POST", "DELETE", "HEAD", "OPTIONS", "other"},
    "fetch_site": {"missing", "same-origin", "same-site", "cross-site", "none", "other"},
    "fetch_mode": {"missing", "navigate", "cors", "no-cors", "same-origin", "websocket", "other"},
    "fetch_dest": {"missing", "document", "empty", "iframe", "other"},
    "grant_type": {"authorization_code", "refresh_token", "other"},
    "client_auth": {"none", "basic", "other"},
    "rpc_method": {"initialize", "ping", "notifications/initialized", "tools/list", "tools/call",
                   "resources/list", "resources/templates/list", "prompts/list", "other"},
    "tool": {"entities_status", "configured_action", "other"},
    "oauth_error": {"invalid_request", "invalid_client", "invalid_client_metadata", "access_denied",
                    "invalid_target", "invalid_grant", "temporarily_unavailable", "unsupported_grant_type", "other"},
    "error_class": {"HTTPException", "OAuthError", "ValueError", "other"},
    "content_type": {"json", "form", "other"},
}


def category(field, value):
    """Keep only a known literal; do not stringify a user-supplied value."""
    return value if isinstance(value, str) and value in _CATEGORIES[field] else "other"


def emit(stage, outcome, *, warning=False, **fields):
    if stage not in _STAGES or outcome not in _OUTCOMES:
        return
    record = {"stage": stage, "outcome": outcome}
    for key, value in fields.items():
        if key in _FLAGS and type(value) is bool:
            record[key] = value
        elif key in _COUNTS and type(value) is int and 0 <= value <= 10000:
            record[key] = value
        elif key in _CATEGORIES:
            record[key] = category(key, value)
        elif key in {"request_id", "flow_id"} and isinstance(value, str) and re.fullmatch(r"[a-f0-9]{12}", value):
            record[key] = value
        elif key == "version" and isinstance(value, str) and re.fullmatch(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?:b[0-9]{1,3})?", value):
            record[key] = value
    now = time.monotonic()
    while _WINDOW and _WINDOW[0] <= now - 60:
        _WINDOW.popleft()
    if len(_WINDOW) >= _LIMIT:
        return
    _WINDOW.append(now)
    _LOGGER.log(logging.WARNING if warning else logging.INFO, "GROK_CONNECTOR_DIAG %s",
                json.dumps(record, separators=(",", ":"), sort_keys=True))


from .ha_diagnostics import async_get_config_entry_diagnostics  # HA diagnostics entry point
