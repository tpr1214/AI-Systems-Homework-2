import json
import sys
from typing import Any, Dict, List

from agents import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered, Runner
from dotenv import load_dotenv

from agents_config import router_agent, router_structured_agent
from guardrails import demo_output_guardrail, validate_final_output, validate_input, validate_router_output
from memory import load_history, reset_history, save_history
from schemas import RouterOutput


load_dotenv()


def _safe_get(obj: Any, field: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(field, default)
    return getattr(obj, field, default)


def _clean_parameters(router_output: RouterOutput) -> Dict[str, Any]:
    params = router_output.parameters.model_dump()
    allowed: dict[str, list[str]] = {
        "getWeather": ["city"],
        "calculateMath": ["expression_or_problem"],
        "generalChat": ["message"],
    }

    if router_output.intent == "getExchangeRate":
        if params.get("from_currency") and params.get("to_currency"):
            fields = ["from_currency", "to_currency", "amount"]
        else:
            fields = ["currency"]
    else:
        fields = allowed.get(router_output.intent, [])

    return {
        key: value
        for key, value in params.items()
        if key in fields and value not in (None, "", 0.0)
    }


def _print_router_output(router_output: RouterOutput, params_clean: Dict[str, Any]) -> None:
    print("\n[Router] Structured Output:")
    print(
        json.dumps(
            {
                "intent": router_output.intent,
                "parameters": params_clean,
                "confidence": router_output.confidence,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _history_text(messages: List[Dict[str, str]]) -> str:
    if not messages:
        return "No previous messages."
    lines = []
    for msg in messages[-12:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _handoff_input(
    user_input: str,
    router_output: RouterOutput,
    params_clean: Dict[str, Any],
    messages: List[Dict[str, str]],
) -> str:
    if router_output.intent == "generalChat":
        history = _history_text(messages)
    else:
        history = "History intentionally omitted for deterministic task agents."

    return (
        f"Classified intent: {router_output.intent}\n"
        f"Structured parameters: {json.dumps(params_clean, ensure_ascii=False)}\n"
        f"Current user request: {user_input}\n\n"
        f"Conversation history for context:\n{history}"
    )


def _print_run_log(result: Any) -> None:
    last_agent = _safe_get(result, "last_agent")
    last_agent_name = _safe_get(last_agent, "name", "")
    if last_agent_name and last_agent_name != "Router Agent":
        print(f"[Handoff] Router Agent -> {last_agent_name}")

    for item in _safe_get(result, "new_items", []) or []:
        raw = _safe_get(item, "raw_item", item)
        name = _safe_get(raw, "name") or _safe_get(raw, "tool_name")
        args = _safe_get(raw, "arguments")
        output = _safe_get(item, "output")
        item_type = item.__class__.__name__

        if name and "Handoff" not in item_type:
            if args:
                print(f"[Tool] {name}({args})")
            else:
                print(f"[Tool] {name}()")
        if output and "ToolCallOutput" in item_type:
            text = str(output)
            if len(text) > 160:
                text = text[:157] + "..."
            print(f"[Tool Output] {text}")


def _run_router(user_input: str) -> tuple[RouterOutput, Dict[str, Any]]:
    result = Runner.run_sync(router_structured_agent, user_input)
    router_output = result.final_output
    if not isinstance(router_output, RouterOutput):
        raise ValueError("Router did not return RouterOutput")

    params_clean = _clean_parameters(router_output)
    _print_router_output(router_output, params_clean)

    if not validate_router_output(router_output):
        raise ValueError("Router output failed validation")

    return router_output, params_clean


def _run_handoff(
    user_input: str,
    router_output: RouterOutput,
    params_clean: Dict[str, Any],
    messages: List[Dict[str, str]],
) -> str:
    result = Runner.run_sync(
        router_agent,
        _handoff_input(user_input, router_output, params_clean, messages),
        max_turns=10,
    )
    _print_run_log(result)
    return str(result.final_output or "").strip()


def main() -> None:
    demo_output_guardrail()
    messages = load_history()

    while True:
        try:
            raw_input = input("\nAsk something ('/reset' to clear, '/exit' to quit): ")
            user_input = raw_input.strip()
        except EOFError:
            break

        if not user_input:
            print("\n[Input Guardrail] Empty input blocked")
            print("\nFinal Answer:\nPlease enter a valid question.")
            continue

        if user_input == "/exit":
            print("Exiting. Saving history...")
            save_history(messages)
            sys.exit(0)

        if user_input == "/reset":
            messages = reset_history()
            continue

        if not validate_input(user_input):
            print("\n[Input Guardrail] Blocked unsafe input")
            print("\nFinal Answer:\nI cannot process this request due to safety protocols.")
            continue

        try:
            router_output, params_clean = _run_router(user_input)
            messages.append({"role": "user", "content": user_input})

            final_message = _run_handoff(user_input, router_output, params_clean, messages)
            if validate_final_output(final_message):
                print(f"\nFinal Answer:\n{final_message}")
                messages.append({"role": "assistant", "content": final_message})
                save_history(messages)
            else:
                print("\n[Output Guardrail] Blocked unsafe final output")
                print("\nFinal Answer:\nI cannot process this request due to safety protocols.")

        except InputGuardrailTripwireTriggered:
            print("\n[Input Guardrail] Blocked unsafe input")
            print("\nFinal Answer:\nI cannot process this request due to safety protocols.")
        except OutputGuardrailTripwireTriggered:
            print("\n[Output Guardrail] Blocked unsafe output")
            print("\nFinal Answer:\nI cannot process this request due to safety protocols.")
        except Exception as e:
            print(f"\n[Error] {e}")
            print("\nFinal Answer:\nSorry, something went wrong while processing this request.")


if __name__ == "__main__":
    main()
