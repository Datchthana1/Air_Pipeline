import requests as re
import urllib3
import os
from pprint import pprint
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv(dotenv_path=Path(__file__).parent.parent / 'assets' / '.env')

OW_API=os.getenv('OPENWEATHER_API_KEY')
LAT=os.getenv('LATITUDE')
LON=os.getenv('LONGITUDE')
STATION_ID=os.getenv('AIR4THAI_STATIONID')
SUPABASE_URL=os.getenv('SUPABASE_URL')
SUPABASE_KEY=os.getenv('SUPABASE_KEY')

def requests_api_OW(lat, lon, API_key):
    response = re.get(f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_key}&units=metric')
    response_json = response.json()
    response_json['dt'] = datetime.fromtimestamp(response_json['dt'], tz=timezone(timedelta(hours=7))).isoformat()
    response_json['sys']['sunrise'] = datetime.fromtimestamp(response_json['sys']['sunrise']).isoformat()
    response_json['sys']['sunset'] = datetime.fromtimestamp(response_json['sys']['sunset']).isoformat()
    return response_json

def requests_api_AIR4THAI(station_id):
    response = re.get('http://air4thai.pcd.go.th/services/getNewAQI_JSON.php', timeout=10)
    response_json = response.json()
    stations = [s for s in response_json['stations'] if s['stationID'] == station_id]
    return stations[0] if stations else None

def combine_data(LAT, LON, OW_API, STATION_ID):
    requests_api_OW_data = requests_api_OW(LAT, LON, OW_API)
    requests_api_AIR4THAI_data = requests_api_AIR4THAI(STATION_ID)
    combined_data = {
        "Datetime": requests_api_OW_data['dt'],
        "Temperature": requests_api_OW_data['main']['temp'],
        "Humidity": requests_api_OW_data['main']['humidity'],
        "Wind Speed": requests_api_OW_data['wind']['speed'],
        "Pressure": requests_api_OW_data['main']['pressure'],
        "Visibility": requests_api_OW_data.get('visibility'),
        "Cloud": requests_api_OW_data['weather'][0]['description'] if requests_api_OW_data.get('weather') else None,
        "Wind_Direction": requests_api_OW_data['wind'].get('deg'),
        "Wind_Speed": requests_api_OW_data['wind']['speed'],
        "Sea_level": requests_api_OW_data['main'].get('sea_level'),
        "TempMin": requests_api_OW_data['main']['temp_min'],
        "TempMax": requests_api_OW_data['main']['temp_max'],
        "PM2.5": requests_api_AIR4THAI_data['AQILast']['PM25']['value'],
        "AQI": requests_api_AIR4THAI_data['AQILast']['AQI']['aqi'],
        "Area": requests_api_AIR4THAI_data['areaEN'],
        "Station_Name": requests_api_AIR4THAI_data['nameEN'],
    }
    return combined_data

def Connect_to_database():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_data(data: dict):
    client = Connect_to_database()
    client.table('weather_data').insert({
        "datetime":        data['Datetime'],
        "temperature":     data['Temperature'],
        "humidity":        data['Humidity'],
        "wind_speed":      data['Wind_Speed'],
        "pressure":        data['Pressure'],
        "visibility":      data['Visibility'],
        "cloud":           data['Cloud'],
        "wind_direction":  data['Wind_Direction'],
        "sea_level":       data['Sea_level'],
        "temp_min":        data['TempMin'],
        "temp_max":        data['TempMax'],
        "pm25":            data['PM2.5'],
        "area":            data['Area'],
        "station_name":    data['Station_Name'],
    }).execute()
    return {
        "status": "success",
        "message": "Data inserted successfully",
        "status_code": 200
    }