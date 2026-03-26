"""
lab4/tools/weather.py

Simulated weather tool.
Production replacement: swap _fetch_weather() to call a real weather API
(OpenWeatherMap, WeatherAPI, etc). Everything else — validation, error
contract, return shape — stays identical.

Morgan's four checks are applied before any logic runs:
  1. Type check
  2. Empty / whitespace check
  3. Length bound
  4. No shell / SQL / path interpolation (enforced by never using os.system etc.)
"""

from __future__ import annotations

import random


# ---------------------------------------------------------------------------
# Public tool function
# ---------------------------------------------------------------------------

def get_weather(location: str) -> dict:
    """
    Get current weather conditions for a city.

    Returns a dict — never raises. Errors are returned as data so the
    dispatch() layer can serialise them to JSON and return them to the model.

    Args:
        location: City name, e.g. "Denver" or "Paris, France"

    Returns:
        On success: {"error": False, "location": str, "temperature_f": int,
                     "condition": str, "humidity_pct": int}
        On failure: {"error": True, "message": str}
    """
    # --- Morgan check 1: type ---
    if not isinstance(location, str):
        return {
            "error": True,
            "message": f"location must be a string, got {type(location).__name__}",
        }

    # --- Morgan check 2: empty / whitespace ---
    location = location.strip()
    if not location:
        return {
            "error": True,
            "message": "location cannot be empty",
        }

    # --- Morgan check 3: length bound ---
    if len(location) > 200:
        return {
            "error": True,
            "message": "location string too long (max 200 chars)",
        }

    # --- Morgan check 4: no shell / SQL / path interpolation ---
    # All API calls use parameterised requests — location is never
    # interpolated into a shell command or raw SQL string.

    return _fetch_weather(location)


# ---------------------------------------------------------------------------
# Internal implementation (swap this for a real API call)
# ---------------------------------------------------------------------------

_CONDITIONS = ["sunny", "cloudy", "partly cloudy", "rainy", "windy", "snowy"]

def _fetch_weather(location: str) -> dict:
    """
    Simulated weather fetch. Replace with real HTTP call in production.

    Example production replacement:
        import httpx
        resp = httpx.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": os.environ["WEATHER_API_KEY"], "q": location},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "error": False,
            "location": data["location"]["name"],
            "temperature_f": data["current"]["temp_f"],
            "condition": data["current"]["condition"]["text"],
            "humidity_pct": data["current"]["humidity"],
        }
    """
    # Deterministic seed on location name so the same city always returns
    # the same result within a session — useful for testing.
    rng = random.Random(location.lower())

    return {
        "error": False,
        "location": location,
        "temperature_f": rng.randint(20, 105),
        "condition": rng.choice(_CONDITIONS),
        "humidity_pct": rng.randint(10, 95),
    }
