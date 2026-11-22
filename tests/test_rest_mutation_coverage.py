"""Guard every state-changing REST route at both mapping and handler level.

A route is not protected merely because an action exists in the policy map:
its endpoint must actually invoke the shared authorization gate, or implement
one of the narrowly documented separate confirmation gates.
"""
import builtins
import dis
import re

from micro_helper.api import (
    CHAT_ACTION,
    REST_POLICY,
    app,
    _consume_tool_confirmation,
    _normalize_rest_arguments,
    _normalize_tool_arguments,
    _record_tool_audit,
    _resolve_rest_action,
    database,
)
from micro_helper.trust_policy import evaluate_action, permission_key


SEPARATE_GATE_CALLS = {
    # Issues a one-time token only after resolving and evaluating the target action.
    ("POST", "/v1/actions/confirm"): {
        "_resolve_rest_action", "_normalize_rest_arguments", "evaluate_action",
        "REST_POLICY", "_record_tool_audit", "database",
    },
    # Tool confirmation validates the allowlisted tool and policy before issuing.
    ("POST", "/v1/tools/{tool_id}/confirm"): {
        "TOOL_ACTIONS", "_normalize_tool_arguments", "evaluate_action",
        "TOOL_POLICY", "_record_tool_audit", "database",
    },
    # Tool execution re-evaluates policy and consumes a matching one-time token.
    ("POST", "/v1/tools/{tool_id}/execute"): {
        "TOOL_ACTIONS", "_normalize_tool_arguments", "evaluate_action",
        "TOOL_POLICY", "_consume_tool_confirmation",
    },
}

SEPARATE_GATE_REQUIRED_CALLS = {
    ("POST", "/v1/actions/confirm"): {
        "_resolve_rest_action", "_normalize_rest_arguments",
        "evaluate_action", "_record_tool_audit",
    },
    ("POST", "/v1/tools/{tool_id}/confirm"): {
        "_normalize_tool_arguments", "evaluate_action", "_record_tool_audit",
    },
    ("POST", "/v1/tools/{tool_id}/execute"): {
        "_normalize_tool_arguments", "evaluate_action",
        "_consume_tool_confirmation", "_record_tool_audit",
    },
}

PLACEHOLDER_VALUES = {
    "memory_id": "1",
    "preference_id": "1",
    "task_id": "sample-task",
    "plan_id": "sample-plan",
    "tool_id": "memory.list",
}


def sample_path(route_path: str) -> str:
    return re.sub(
        r"\{([^{}]+)\}",
        lambda match: PLACEHOLDER_VALUES[match.group(1)],
        route_path,
    )


def endpoint_names(endpoint) -> set[str]:
    code = getattr(endpoint, "__code__", None)
    return set(code.co_names) if code is not None else set()


def endpoint_calls_name(endpoint, name: str) -> bool:
    """Require the loaded callable to be invoked, not merely referenced.

    A nearby CALL is insufficient: returning the gate reference alongside an
    unrelated function call used to satisfy the old check.
    """
    if getattr(endpoint, "__code__", None) is None:
        return False

    namespace = getattr(endpoint, "__globals__", {})
    builtin_namespace = getattr(endpoint, "__builtins__", builtins)
    if not isinstance(builtin_namespace, dict):
        builtin_namespace = vars(builtin_namespace)
    code = endpoint.__code__
    closure = getattr(endpoint, "__closure__", None) or ()
    closure_namespace = dict(zip(code.co_freevars, (cell.cell_contents for cell in closure)))

    instructions = list(dis.get_instructions(endpoint))
    for index, instruction in enumerate(instructions):
        if instruction.opname not in {"LOAD_GLOBAL", "LOAD_DEREF", "LOAD_NAME"}:
            continue
        if instruction.argval != name:
            continue

        for candidate in instructions[index + 1:index + 12]:
            if candidate.opname in {"CALL", "CALL_FUNCTION", "CALL_METHOD"}:
                return True
            if candidate.opname in {
                "RETURN_VALUE", "POP_TOP", "STORE_FAST", "STORE_DEREF", "STORE_GLOBAL"
            }:
                break
            if candidate.opname in {"LOAD_GLOBAL", "LOAD_DEREF", "LOAD_NAME"}:
                # Another callable may be the real callee before this CALL.
                value = namespace.get(candidate.argval)
                if value is None:
                    value = closure_namespace.get(candidate.argval)
                if value is None:
                    value = builtin_namespace.get(candidate.argval)
                if callable(value):
                    break
    return False


def route_gate_errors(routes) -> list[str]:
    """Return actionable failures for unprotected state-changing local routes."""
    uncovered = []

    for route in routes:
        route_path = getattr(route, "path", "")
        if not route_path.startswith("/v1/"):
            continue

        methods = getattr(route, "methods", set()) or set()
        for method in sorted(methods & {"POST", "PUT", "PATCH", "DELETE"}):
            key = (method, route_path)
            names = endpoint_names(route.endpoint)

            if key in SEPARATE_GATE_CALLS:
                missing = SEPARATE_GATE_CALLS[key] - names
                if missing:
                    uncovered.append(
                        f"{method} {route_path} separate gate missing references: "
                        + ", ".join(sorted(missing))
                    )
                missing_calls = [
                    name for name in sorted(SEPARATE_GATE_REQUIRED_CALLS[key])
                    if not endpoint_calls_name(route.endpoint, name)
                ]
                if missing_calls:
                    uncovered.append(
                        f"{method} {route_path} separate gate does not call: "
                        + ", ".join(missing_calls)
                    )
                continue

            resolved = _resolve_rest_action(method, sample_path(route_path))
            if resolved is None:
                uncovered.append(f"{method} {route_path} has no policy action")
            if not endpoint_calls_name(route.endpoint, "_authorize_rest_mutation"):
                uncovered.append(
                    f"{method} {route_path} does not call _authorize_rest_mutation"
                )

    return uncovered


def test_every_state_changing_local_rest_route_has_an_explicit_policy_gate():
    uncovered = route_gate_errors(app.routes)
    assert not uncovered, (
        "State-changing local REST route(s) are not fully protected: "
        + "; ".join(uncovered)
    )


def test_chat_is_the_only_builtin_allow_grant():
    assert REST_POLICY.grants == frozenset({permission_key(CHAT_ACTION)})
    assert CHAT_ACTION.capability == "conversation"
    assert CHAT_ACTION.operation == "append"
    resolved = _resolve_rest_action("POST", "/v1/chat")
    assert resolved is not None
    assert resolved[0] == "rest:POST:/v1/chat"


def test_route_gate_checker_rejects_a_dead_reference_to_the_gate():
    from micro_helper.api import _authorize_rest_mutation
    from types import SimpleNamespace

    def endpoint_that_only_references_the_gate():
        return _authorize_rest_mutation

    route = SimpleNamespace(
        path="/v1/test-reference-only",
        methods={"POST"},
        endpoint=endpoint_that_only_references_the_gate,
    )

    errors = route_gate_errors([route])
    assert any("does not call _authorize_rest_mutation" in error for error in errors)


def test_route_gate_checker_detects_an_unprotected_handler():
    from types import SimpleNamespace

    def unprotected_endpoint():
        return {"ok": True}

    route = SimpleNamespace(
        path="/v1/test-unprotected",
        methods={"POST"},
        endpoint=unprotected_endpoint,
    )

    errors = route_gate_errors([route])
    assert any("has no policy action" in error for error in errors)
    assert any("does not call _authorize_rest_mutation" in error for error in errors)


def test_route_gate_checker_rejects_a_reference_followed_by_an_unrelated_call():
    from micro_helper.api import _authorize_rest_mutation
    from types import SimpleNamespace

    def unrelated_helper():
        return True

    def endpoint_that_never_calls_the_gate():
        return _authorize_rest_mutation, unrelated_helper()

    route = SimpleNamespace(
        path="/v1/test-unrelated-call",
        methods={"POST"},
        endpoint=endpoint_that_never_calls_the_gate,
    )

    errors = route_gate_errors([route])
    assert any("does not call _authorize_rest_mutation" in error for error in errors)


def test_route_gate_checker_requires_real_calls_in_separate_confirmation_routes():
    from types import SimpleNamespace

    def unrelated_helper():
        return True

    def endpoint_that_only_references_confirmation_dependencies():
        return (
            _resolve_rest_action,
            _normalize_rest_arguments,
            evaluate_action,
            REST_POLICY,
            _record_tool_audit,
            database,
            unrelated_helper(),
        )

    route = SimpleNamespace(
        path="/v1/actions/confirm",
        methods={"POST"},
        endpoint=endpoint_that_only_references_confirmation_dependencies,
    )

    errors = route_gate_errors([route])
    assert any("separate gate does not call:" in error for error in errors)
