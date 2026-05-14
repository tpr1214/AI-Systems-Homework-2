import os
from typing import Optional

import requests
from agents import function_tool
from dotenv import load_dotenv
from simpleeval import SimpleEval


def _normalize_place(city: str) -> str:
    country_map = {
        "thailand": "Bangkok",
        "israel": "Tel Aviv",
        "uk": "London",
        "united kingdom": "London",
        "canada": "Toronto",
        "תאילנד": "Bangkok",
        "ישראל": "Tel Aviv",
        "קנדה": "Toronto",
    }
    clean = city.strip()
    return country_map.get(clean.casefold(), clean)


@function_tool
def getWeather(city: str) -> str:
    """
    Fetch current weather for a city using OpenWeatherMap.
    Requires OPENWEATHER_API_KEY in `.env`.
    """
    load_dotenv()
    clean_city = _normalize_place(city)
    if not clean_city:
        return "Error: city is empty"

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Error: Missing OPENWEATHER_API_KEY in .env"

    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": clean_city, "appid": api_key, "units": "metric"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        temp_c = float(data["main"]["temp"])
        description = str((data.get("weather") or [{}])[0].get("description", "")).strip()
        return f"In {clean_city} it is {temp_c}°C, {description}."
    except Exception as e:
        return f"Could not fetch weather data: {e}"


@function_tool
def getExchangeRate(currencyCode: str) -> str:
    """
    Fetch the ILS rate for a currency code.
    Uses EXCHANGERATE_API_KEY when present, otherwise falls back to open.er-api.com.
    """
    load_dotenv()
    code = currencyCode.strip().upper()
    if not code:
        return "Error: currencyCode is empty"
    if len(code) != 3 or not code.isalpha():
        return f"Error: invalid currency code '{currencyCode}'"

    try:
        api_key: Optional[str] = os.getenv("EXCHANGERATE_API_KEY")
        if api_key:
            url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{code}"
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return str(float(data["conversion_rates"]["ILS"]))

        resp = requests.get(f"https://open.er-api.com/v6/latest/{code}", timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return str(float(data["rates"]["ILS"]))
    except Exception as e:
        return f"Error fetching exchange rate: {e}"


@function_tool
def calculateMath(expression: str) -> str:
    """
    Deterministically evaluate a clean math expression and return the result.
    """
    expr = expression.strip()
    if not expr:
        return "Error: expression is empty"

    evaluator = SimpleEval()
    evaluator.functions = {"abs": abs, "round": round}
    evaluator.names = {}

    try:
        value = evaluator.eval(expr)
        num = float(value)
        if num == int(num):
            return str(int(num))
        return str(num)
    except Exception as e:
        return f"Expression did not evaluate to a number: {e}"
