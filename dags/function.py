import requests as re
import urllib3
import os
from supabase import create_client, Client
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv(dotenv_path=Path(__file__).parent.parent / "assets" / ".env")

OW_API = os.getenv("OPENWEATHER_API_KEY")
LAT = os.getenv("LATITUDE")
LON = os.getenv("LONGITUDE")
STATION_ID = os.getenv("AIR4THAI_STATIONID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TZ_BKK = timezone(timedelta(hours=7))


def requests_api_OW(lat, lon, API_key):
    try:
        response = re.get(
            f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_key}&units=metric"
        )
        if lat is None or lon is None:
            raise ValueError("Latitude and Longitude must be provided")
        response.raise_for_status()
        response_json = response.json()
        response_json["dt"] = datetime.fromtimestamp(
            response_json["dt"], tz=TZ_BKK
        ).isoformat()
        response_json["sys"]["sunrise"] = datetime.fromtimestamp(
            response_json["sys"]["sunrise"], tz=TZ_BKK
        ).isoformat()
        response_json["sys"]["sunset"] = datetime.fromtimestamp(
            response_json["sys"]["sunset"], tz=TZ_BKK
        ).isoformat()
        return response_json
    except Exception as e:
        raise ValueError(f"Error fetching data from OpenWeather API: {e}")


def requests_api_AIR4THAI(station_id):
    try:
        response = re.get(
            "http://air4thai.pcd.go.th/services/getNewAQI_JSON.php", timeout=30
        )
        if response.status_code != 200:
            return None
        response_json = response.json()
        stations = [
            s for s in response_json["stations"] if s["stationID"] == station_id
        ]
        return stations[0] if stations else None
    except Exception:
        return None


def combine_data(LAT, LON, OW_API, STATION_ID):
    requests_api_OW_data = requests_api_OW(LAT, LON, OW_API)
    requests_api_AIR4THAI_data = requests_api_AIR4THAI(STATION_ID)
    combined_data = {
        "Datetime": requests_api_OW_data["dt"],
        "Temperature": requests_api_OW_data["main"]["temp"],
        "Humidity": requests_api_OW_data["main"]["humidity"],
        "Pressure": requests_api_OW_data["main"]["pressure"],
        "Visibility": requests_api_OW_data.get("visibility"),
        "Cloud": (
            requests_api_OW_data["weather"][0]["description"]
            if requests_api_OW_data.get("weather")
            else None
        ),
        "Wind_Direction": requests_api_OW_data["wind"].get("deg"),
        "Wind_Speed": requests_api_OW_data["wind"]["speed"],
        "Sea_level": requests_api_OW_data["main"].get("sea_level"),
        "TempMin": requests_api_OW_data["main"]["temp_min"],
        "TempMax": requests_api_OW_data["main"]["temp_max"],
        "PM2.5": (
            requests_api_AIR4THAI_data["AQILast"]["PM25"]["value"]
            if requests_api_AIR4THAI_data
            else None
        ),
        "AQI": (
            requests_api_AIR4THAI_data["AQILast"]["AQI"]["aqi"]
            if requests_api_AIR4THAI_data
            else None
        ),
        "Area": (
            requests_api_AIR4THAI_data["areaEN"] if requests_api_AIR4THAI_data else None
        ),
        "Station_Name": (
            requests_api_AIR4THAI_data["nameEN"] if requests_api_AIR4THAI_data else None
        ),
    }
    return combined_data


_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY is not set")
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def insert_data(data: dict, table_name: str = "weather_data"):
    client = get_supabase_client()
    client.table(table_name).insert(
        {
            "datetime": data["Datetime"],
            "temperature": data["Temperature"],
            "humidity": data["Humidity"],
            "wind_speed": data["Wind_Speed"],
            "pressure": data["Pressure"],
            "visibility": data["Visibility"],
            "cloud": data["Cloud"],
            "wind_direction": data["Wind_Direction"],
            "sea_level": data["Sea_level"],
            "temp_min": data["TempMin"],
            "temp_max": data["TempMax"],
            "pm25": data["PM2.5"],
            "AQI": data["AQI"],
            "area": data["Area"],
            "station_name": data["Station_Name"],
        }
    ).execute()
    return {
        "status": "success",
        "message": "Data inserted successfully",
        "status_code": 200,
    }


def process_daily_data(target_date: date | None = None):
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    client = get_supabase_client()
    target = target_date or (date.today() - timedelta(days=1))
    target_str = target.isoformat()
    print(f"Processing data for date: {target_str}")

    response = (
        client.table("weather_data")
        .select("*")
        .gte("datetime", f"{target_str}T00:00:00+07:00")
        .lt("datetime", f"{(target + timedelta(days=1)).isoformat()}T00:00:00+07:00")
        .execute()
    )

    if not response.data:
        return []

    df = pd.DataFrame(response.data)

    df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert(
        "Asia/Bangkok"
    )
    df.set_index("created_at", inplace=True)

    df = df[df.index.date == target]

    if df.empty:
        return []

    df_daily = df.resample("D").agg(
        {
            "temperature": "mean",
            "humidity": "mean",
            "wind_speed": "mean",
            "pressure": "mean",
            "visibility": "mean",
            "cloud": lambda x: x.mode()[0] if not x.mode().empty else None,
            "wind_direction": lambda x: x.mode()[0] if not x.mode().empty else None,
            "sea_level": "mean",
            "temp_min": "min",
            "temp_max": "max",
            "pm25": "mean",
            "area": lambda x: x.mode()[0] if not x.mode().empty else None,
            "station_name": lambda x: x.mode()[0] if not x.mode().empty else None,
        }
    )

    df_daily["AQI"] = df_daily["pm25"].apply(
        lambda v: calculate_aqi_pm25(v) if v is not None and not pd.isna(v) else None
    )

    df_daily = df_daily.reset_index()
    df_daily = df_daily.rename(columns={"created_at": "datetime"})

    df_daily["datetime"] = df_daily["datetime"].dt.normalize().dt.tz_localize(None)

    records = df_daily.to_dict(orient="records")
    return records


def insert_daily_data(records: list, table_name: str = "weather_data_daily"):
    if not records:
        return None
    client = get_supabase_client()

    def to_int(val):
        return int(round(val)) if val is not None and not pd.isna(val) else None

    def to_float(val):
        return float(val) if val is not None and not pd.isna(val) else None

    rows = [
        {
            "datetime": (
                r["datetime"].isoformat()
                if hasattr(r["datetime"], "isoformat")
                else str(r["datetime"])
            ),
            "temperature": to_float(r["temperature"]),
            "humidity": to_int(r["humidity"]),
            "wind_speed": to_float(r["wind_speed"]),
            "pressure": to_int(r["pressure"]),
            "visibility": to_int(r["visibility"]),
            "cloud": r["cloud"],
            "wind_direction": to_int(r["wind_direction"]),
            "sea_level": to_int(r["sea_level"]),
            "temp_min": to_float(r["temp_min"]),
            "temp_max": to_float(r["temp_max"]),
            "pm25": to_float(r["pm25"]),
            "AQI": to_int(r["AQI"]),
            "area": r["area"],
            "created_at": datetime.now(ZoneInfo("Asia/Bangkok")).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            ),
            "day_of_week": (
                r["datetime"].strftime("%A")
                if hasattr(r["datetime"], "strftime")
                else pd.to_datetime(r["datetime"]).strftime("%A")
            ),
            "station_name": r["station_name"],
        }
        for r in records
    ]
    client.table(table_name).upsert(rows, on_conflict="datetime").execute()
    return {"status": "success", "rows_inserted": len(rows)}


_PM25_BREAKPOINTS = [
    (0.0, 15.0, 0, 25),
    (15.1, 25.0, 26, 50),
    (25.1, 37.5, 51, 100),
    (37.6, 75.0, 101, 200),
    (75.1, 150.0, 201, 300),
]


def calculate_aqi_pm25(pm25: float) -> int:
    pm25 = round(pm25, 1)
    for bp_lo, bp_hi, aqi_lo, aqi_hi in _PM25_BREAKPOINTS:
        if bp_lo <= pm25 <= bp_hi:
            return round((aqi_hi - aqi_lo) / (bp_hi - bp_lo) * (pm25 - bp_lo) + aqi_lo)
    if pm25 > 500.4:
        return 500
    return 0
    # Reference: https://aqihub.info/indices/thailand
