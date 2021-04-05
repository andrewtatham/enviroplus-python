import requests
import config_helper

config = config_helper.get_config()["openweathermap"];

api_key = config["api_key"]
city = config["city"]

url = 'https://api.openweathermap.org/data/2.5/weather'
data = {'q': city, 'appid': api_key}

receive = requests.get(url, data=data)

print(receive.status_code)
print(receive.reason)
print(receive.text)
