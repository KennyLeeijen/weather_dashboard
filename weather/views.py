import requests
import pytz
import logging
from django.shortcuts import render
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)

# Dictionary for translating weather descriptions to Dutch
WEATHER_TRANSLATIONS = {
    "clear sky": "Onbewolkt",
    "few clouds": "Licht bewolkt",
    "scattered clouds": "Verspreide wolken",
    "broken clouds": "Gedeeltelijk bewolkt",
    "shower rain": "Motregen",
    "rain": "Regen",
    "thunderstorm": "Onweer",
    "snow": "Sneeuw",
    "mist": "Mist",
    "sunny": "Zonnig",
}

def get_weather(request):
    api_key = settings.API_KEY
    city = request.GET.get('city', 'Heesch')

    # Get Latitude and Longitude for the city using Current Weather Data API
    current_weather_url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={api_key}'

    try:
        # Fetch current weather data to get latitude and longitude
        current_response = requests.get(current_weather_url)
        current_response.raise_for_status()
        weather_data = current_response.json()
        logger.info("Weather data: %s", weather_data)

        lat = weather_data['coord']['lat']
        lon = weather_data['coord']['lon']

        # Fetch weather data using One Call API 3.0
        one_call_url = f'https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&units=metric&appid={api_key}'
        one_call_response = requests.get(one_call_url)
        one_call_response.raise_for_status()
        one_call_data = one_call_response.json()
        logger.info("One Call data: %s", one_call_data)

        # Extract daily forecasts and convert Unix timestamps to datetime objects
        daily_forecast = []
        for day in one_call_data.get('daily', []):
            date_object = datetime.fromtimestamp(day['dt'])  # Convert the timestamp to a datetime object
            daily_forecast.append({
                'date': date_object,
                'temperature': day['temp']['day'],
                'icon': day['weather'][0]['icon'],
                'description': day['weather'][0]['description'],
                'summary': day.get('summary', ''),  # Using the summary field if available
            })

        # Fetch UV Index data
        uv_url = f'http://api.openweathermap.org/data/2.5/uvi?lat={lat}&lon={lon}&appid={api_key}'
        uv_response = requests.get(uv_url)
        uv_response.raise_for_status()
        uv_data = uv_response.json()
        uv_index = uv_data['value']

        # Extract current weather details
        current_weather = one_call_data.get('current', {})
        description = current_weather.get('weather', [])[0].get('description', '').lower()
        translated_description = WEATHER_TRANSLATIONS.get(description, description)

        # Extract hourly forecast data and convert Unix timestamps to datetime objects
        hourly_forecast = []
        timezone = pytz.timezone(settings.TIME_ZONE)  # Define timezone
        for hour in one_call_data.get('hourly', []):
            hour_dt = datetime.fromtimestamp(hour['dt'], timezone)  # Convert timestamp to datetime object
            hourly_forecast.append({
                'dt': hour_dt,
                'temperature': hour['temp'],
                'icon': hour['weather'][0]['icon'],
                'wind_speed': hour['wind_speed'],
            })

        # Extract alerts if available and format them
        alerts = []
        for alert in one_call_data.get('alerts', []):
            alerts.append({
                'event': alert.get('event'),
                'description': alert.get('description'),
                'start': datetime.fromtimestamp(alert.get('start')),
                'end': datetime.fromtimestamp(alert.get('end')),
            })

        # Convert sunrise and sunset from UNIX timestamp to datetime object
        sunrise = datetime.fromtimestamp(current_weather.get('sunrise'), timezone)
        sunset = datetime.fromtimestamp(current_weather.get('sunset'), timezone)

        # Get the current time and date
        now = datetime.now(timezone)
        formatted_time = now.strftime("%H:%M")
        current_date = now.strftime("%A, %d %B")  # Rename this variable to avoid conflicts

        # Prepare context data to send to the template
        context = {
            'city': weather_data.get('name'),
            'temperature': current_weather.get('temp'),
            'feels_like': current_weather.get('feels_like'),
            'description': translated_description,
            'icon': current_weather.get('weather', [])[0].get('icon'),
            'sunrise': sunrise,
            'sunset': sunset,
            'humidity': current_weather.get('humidity'),
            'wind_speed': current_weather.get('wind_speed'),
            'pressure': current_weather.get('pressure'),
            'daily_forecast': daily_forecast,
            'hourly_forecast': hourly_forecast,
            'time': formatted_time,
            'current_date': current_date,
            'uv_index': uv_index,
            'alerts': alerts,
            'lat': lat,
            'lon': lon,
            'API_KEY': settings.API_KEY,
        }
    except requests.exceptions.RequestException as e:
        logger.error("Request failed: %s", e)
        context = {
            'error': 'Kon de weergegevens niet ophalen. Probeer het later opnieuw.',
        }

    return render(request, 'weather/dashboard.html', context)