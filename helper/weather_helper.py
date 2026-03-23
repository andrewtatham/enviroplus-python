import logging

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Horsforth, Leeds
DEFAULT_LOCATION = {
	"name": "Horsforth, Leeds",
	"latitude": 53.8366,
	"longitude": -1.6422,
	"timezone": "Europe/London",
}


def get_today_forecast(location=None, timeout_seconds=10):
	"""Return today's forecast min/max temperatures (deg C)."""
	if location is None:
		location = DEFAULT_LOCATION

	params = {
		"latitude": location["latitude"],
		"longitude": location["longitude"],
		"timezone": location["timezone"],
		"daily": "temperature_2m_max,temperature_2m_min",
		"forecast_days": 1,
	}

	try:
		response = requests.get(OPEN_METEO_URL, params=params, timeout=timeout_seconds)
		response.raise_for_status()
		payload = response.json()
		daily = payload.get("daily", {})

		forecast_days = daily.get("time", [])
		highs = daily.get("temperature_2m_max", [])
		lows = daily.get("temperature_2m_min", [])

		if not forecast_days or not highs or not lows:
			logging.warning("Weather payload missing daily forecast fields")
			return None

		return {
			"location": location["name"],
			"date": forecast_days[0],
			"high_c": float(highs[0]),
			"low_c": float(lows[0]),
			"source": "open-meteo",
		}
	except (requests.RequestException, ValueError, TypeError) as ex:
		logging.warning("Failed to fetch weather forecast: %s", ex)
		return None


def is_today_low_below(threshold_c, forecast=None):
	if forecast is None:
		forecast = get_today_forecast()
	if not forecast:
		return False
	return float(forecast["low_c"]) < float(threshold_c)


if __name__ == "__main__":
	print(get_today_forecast())
