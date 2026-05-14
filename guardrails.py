import re
from typing import Any

from agents import Agent, GuardrailFunctionOutput, RunContextWrapper, input_guardrail, output_guardrail

from schemas import RouterOutput, RouterParameters


UNSAFE_PATTERNS = [
    r"\bpolitical\b",
    r"\bgovernment\b",
    r"\belection\b",
    r"\bwar\b",
    r"\bmalware\b",
    r"\bhack(?:ing)?\b",
    r"\bphishing\b",
    r"steal password",
    r"bypass security",
    r"פוליטיקה",
    r"ממשלה",
    r"בחירות",
    r"מלחמה",
    r"פריצה",
    r"סיסמ",
]


def _input_text(input_data: str | list[Any]) -> str:
    if isinstance(input_data, str):
        return input_data
    parts: list[str] = []
    for item in input_data:
        if isinstance(item, dict):
            content = item.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                parts.extend(str(part.get("text", "")) for part in content if isinstance(part, dict))
        else:
            parts.append(str(item))
    return "\n".join(parts)


def validate_input(user_input: str) -> bool:
    """
    Input guardrails:
    1. Block empty/invalid input.
    2. Block unsafe topics before model execution.
    """
    if not user_input or not user_input.strip():
        return False

    text_cf = user_input.casefold()
    return not any(re.search(pattern, text_cf, re.IGNORECASE) for pattern in UNSAFE_PATTERNS)


def validate_router_output(output: RouterOutput) -> bool:
    """
    Router output guardrail: verify intent, parameters object, confidence,
    and minimum required parameters for tool-backed intents.
    """
    allowed_intents = {"getWeather", "calculateMath", "getExchangeRate", "generalChat"}
    if output.intent not in allowed_intents:
        return False
    if not isinstance(output.parameters, RouterParameters):
        return False
    if not (0.0 <= output.confidence <= 1.0):
        return False

    p = output.parameters
    if output.intent == "getWeather":
        return bool(p.city)
    if output.intent == "calculateMath":
        return bool(p.expression_or_problem)
    if output.intent == "getExchangeRate":
        has_direct = bool(p.currency)
        has_conversion = bool(p.from_currency and p.to_currency and p.amount is not None)
        return has_direct or has_conversion
    if output.intent == "generalChat":
        return bool(p.message)
    return False


def validate_final_output(output: str) -> bool:
    """
    Final output guardrails:
    1. Output must be non-empty.
    2. Output must not leak secrets or unsafe credential-related text.
    """
    if not output or not output.strip():
        return False

    unsafe_patterns = [
        r"sk-[a-zA-Z0-9_-]{20,}",
        r"password\s*(is|:)",
        r"api[_ -]?key\s*(is|:)",
        r"secret\s*(is|:)",
        r"credit card",
    ]
    return not any(re.search(pattern, output, re.IGNORECASE) for pattern in unsafe_patterns)


@input_guardrail(name="local_input_safety", run_in_parallel=False)
def sdk_input_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, input_data: str | list[Any]
) -> GuardrailFunctionOutput:
    text = _input_text(input_data)
    return GuardrailFunctionOutput(
        output_info={"checked_by": "local_input_safety"},
        tripwire_triggered=not validate_input(text),
    )


@output_guardrail(name="router_structure_validation")
def sdk_router_output_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, output: RouterOutput
) -> GuardrailFunctionOutput:
    return GuardrailFunctionOutput(
        output_info={"intent": getattr(output, "intent", None)},
        tripwire_triggered=not validate_router_output(output),
    )


@output_guardrail(name="final_answer_safety")
def sdk_final_output_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, output: str
) -> GuardrailFunctionOutput:
    return GuardrailFunctionOutput(
        output_info={"checked_by": "final_answer_safety"},
        tripwire_triggered=not validate_final_output(str(output)),
    )


def demo_output_guardrail() -> None:
    """Demonstrate that invalid router structure is blocked."""
    mock = RouterOutput(
        intent="generalChat",
        parameters=RouterParameters(message=""),
        confidence=1.0,
    )
    if not validate_router_output(mock):
        print("[Output Guardrail Demo] Invalid router output blocked")
