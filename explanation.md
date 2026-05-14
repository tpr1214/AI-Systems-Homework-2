# Homework 2 - Multi-Agent System: Architecture Explanation

## Architecture

The system is implemented with the OpenAI Agents SDK. The main loop in `main.py` uses this flow:

```text
User input
  -> local + SDK input guardrails
  -> Router Structured Agent with output_type=RouterOutput
  -> router output validation
  -> Router Agent handoff to a task agent
  -> task agent calls deterministic tools when needed
  -> SDK + local final output guardrails
  -> final answer + history save
```

The router classification is produced by an SDK `Agent` with structured output, not by parsing free text.

## Agents

| Agent | Responsibility |
|---|---|
| Router Structured Agent | Few-shot intent classification into `getWeather`, `calculateMath`, `getExchangeRate`, or `generalChat`; returns `intent`, `parameters`, and `confidence`. |
| Router Agent | Performs real SDK handoffs using `handoffs=[...]`. It does not answer directly. |
| Weather Agent | Handles weather questions and calls `getWeather`. |
| Math Agent | Translates direct math or word problems into clean expressions and calls `calculateMath`. |
| Exchange Agent | Handles exchange-rate and currency-conversion questions using `getExchangeRate` and `calculateMath`. |
| General Chat Agent | Handles safe general chat with a sarcastic but helpful Hebrew persona and conversation memory. |

## Tools

| Tool | Purpose |
|---|---|
| `getWeather(city)` | Fetches current weather from OpenWeatherMap. |
| `calculateMath(expression)` | Deterministically evaluates a clean math expression with `simpleeval`. |
| `getExchangeRate(currencyCode)` | Fetches ILS exchange rates using an API key when available, with a fallback public API. |

## Handoffs

The Router Agent is configured with real OpenAI Agents SDK handoffs:

```python
router_agent = Agent(
    name="Router Agent",
    handoffs=[weather_agent, math_agent, exchange_agent, chat_agent],
)
```

At runtime the console prints the observed transition, for example:

```text
[Handoff] Router Agent -> Weather Agent
```

## Guardrails

Input guardrails:

- Empty or whitespace-only input is blocked before model execution.
- Unsafe topics such as malware, hacking, phishing, password theft, politics, elections, government, and war are blocked.

Output guardrails:

- Router structured output must match the `RouterOutput` schema, use an allowed intent, have confidence between 0 and 1, and include required parameters.
- Final answers must be non-empty and must not leak API keys, passwords, secrets, or credit-card-like sensitive content.

The project also includes an output guardrail demo printed at startup:

```text
[Output Guardrail Demo] Invalid router output blocked
```

## Memory

Memory is stored in `history.json` next to the code. On startup, `load_history()` loads previous user/assistant messages. After successful interactions, `save_history()` writes the updated history. The `/reset` command deletes the history file and starts a fresh conversation. General chat receives recent history so it can answer questions like "What do you remember about me?"

## Files

| File | Purpose |
|---|---|
| `main.py` | CLI loop, SDK runs, logging, local validation, memory save/reset. |
| `agents_config.py` | Agent definitions and SDK handoff wiring. |
| `prompts.py` | All agent prompts and few-shot router examples. |
| `schemas.py` | Pydantic structured output schema. |
| `guardrails.py` | Local and SDK input/output guardrails. |
| `tools.py` | Deterministic SDK function tools. |
| `memory.py` | Persistent conversation history. |
| `test_runner.py` | Scripted workflow demo that writes `run_log.txt`. |
