"""Independent paths and bounds of the community connector."""
DOMAIN = 'grok_connector'
VERSION = '2026.10.5.1'
MCP_PATH = '/api/grok_connector/mcp'
OAUTH_PATH = '/api/grok_connector/oauth'
RESOURCE_METADATA_PATH = '/.well-known/oauth-protected-resource' + MCP_PATH
SERVER_METADATA_PATH = '/.well-known/oauth-authorization-server' + OAUTH_PATH
MAX_ENTITIES = 64
