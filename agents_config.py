import os

from agents import Agent, handoff

from guardrails import sdk_final_output_guardrail, sdk_input_guardrail, sdk_router_output_guardrail
from prompts import (
    CHAT_AGENT_PROMPT,
    EXCHANGE_AGENT_PROMPT,
    MATH_AGENT_PROMPT,
    ROUTER_HANDOFF_PROMPT,
    ROUTER_STRUCTURED_PROMPT,
    WEATHER_AGENT_PROMPT,
)
from schemas import RouterOutput
from tools import calculateMath, getExchangeRate, getWeather


MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


router_structured_agent = Agent(
    name="Router Structured Agent",
    model=MODEL,
    instructions=ROUTER_STRUCTURED_PROMPT,
    output_type=RouterOutput,
    input_guardrails=[sdk_input_guardrail],
    output_guardrails=[sdk_router_output_guardrail],
)

weather_agent = Agent(
    name="Weather Agent",
    model=MODEL,
    handoff_description="Specialist for weather questions and travel-weather decisions.",
    instructions=WEATHER_AGENT_PROMPT,
    tools=[getWeather],
    output_guardrails=[sdk_final_output_guardrail],
)

math_agent = Agent(
    name="Math Agent",
    model=MODEL,
    handoff_description="Specialist for direct calculations and math word problems.",
    instructions=MATH_AGENT_PROMPT,
    tools=[calculateMath],
    output_guardrails=[sdk_final_output_guardrail],
)

exchange_agent = Agent(
    name="Exchange Agent",
    model=MODEL,
    handoff_description="Specialist for exchange rates and currency conversions.",
    instructions=EXCHANGE_AGENT_PROMPT,
    tools=[getExchangeRate, calculateMath],
    output_guardrails=[sdk_final_output_guardrail],
)

chat_agent = Agent(
    name="General Chat Agent",
    model=MODEL,
    handoff_description="Specialist for safe general chat, persona, and memory questions.",
    instructions=CHAT_AGENT_PROMPT,
    output_guardrails=[sdk_final_output_guardrail],
)

router_agent = Agent(
    name="Router Agent",
    model=MODEL,
    instructions=ROUTER_HANDOFF_PROMPT,
    handoffs=[
        handoff(weather_agent, tool_name_override="transfer_to_weather_agent"),
        handoff(math_agent, tool_name_override="transfer_to_math_agent"),
        handoff(exchange_agent, tool_name_override="transfer_to_exchange_agent"),
        handoff(chat_agent, tool_name_override="transfer_to_general_chat_agent"),
    ],
    input_guardrails=[sdk_input_guardrail],
)
