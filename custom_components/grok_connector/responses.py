"""Select only explicitly configured script output, never the full variable scope."""
from collections.abc import Mapping


def response_names(sequence):
    """Inspect HA action containers, never arbitrary service data or templates."""
    for step in sequence:
        if not isinstance(step, dict) or step.get('enabled') is False:
            continue
        name = step.get('response_variable')
        if ('action' in step or 'service' in step) and isinstance(name, str):
            yield name
        for key in ('sequence', 'then', 'else', 'default', 'parallel'):
            if isinstance(children := step.get(key), list):
                yield from response_names(children)
        if isinstance(repeat := step.get('repeat'), dict):
            yield from response_names(repeat.get('sequence', []))
        if isinstance(choices := step.get('choose'), list):
            for choice in choices:
                if isinstance(choice, dict):
                    yield from response_names(choice.get('sequence', []))


def script_response(run_result, sequence):
    """Prefer HA's explicit stop response, then visible named service responses.

    HA owns branching and variable scopes. A response from a nested scope must
    be returned with stop/response_variable or copied into the outer scope by
    the administrator; do not inspect traces or other runs to recover it.
    """
    if run_result is None:
        return None
    if run_result.service_response is not None:
        return run_result.service_response
    variables = run_result.variables
    if not isinstance(variables, Mapping):
        return None
    responses = {name: variables[name] for name in response_names(sequence)
                 if name in variables}
    if len(responses) == 1:
        return next(iter(responses.values()))
    return {'response_variables': responses} if responses else None
