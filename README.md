# Air Quality Pipeline

Air Quality Pipeline was made for learning and doing in my rest time. The purpose is to collect data for training AI Models (Random Forest, Decision Tree, Gradient Boosting, etc.) to predict PM2.5 for the next day.

## Tools

- Apache Airflow
- Pendulum
- Supabase
- Dotenv
- Pprint

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        External APIs                            │
│                                                                 │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │   OpenWeatherMap API │    │     AIR4Thai API (PCD)       │  │
│  │  (api.openweather    │    │  (air4thai.pcd.go.th)        │  │
│  │    map.org)          │    │                              │  │
│  │                      │    │  Station ID: o10             │  │
│  │  - Temperature       │    │  - PM2.5                     │  │
│  │  - Humidity          │    │  - Area / Station Name       │  │
│  │  - Wind Speed/Dir    │    │                              │  │
│  │  - Pressure          │    └──────────────┬───────────────┘  │
│  │  - Visibility        │                   │                  │
│  │  - Cloud             │                   │                  │
│  │  - Sea Level         │                   │                  │
│  │  - Temp Min/Max      │                   │                  │
│  └──────────┬───────────┘                   │                  │
│             │                               │                  │
└─────────────┼───────────────────────────────┼──────────────────┘
              │  HTTP GET                     │  HTTP GET
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Container                             │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   Apache Airflow                          │  │
│  │                  (Schedule: 0 * * * *)                    │  │
│  │                                                           │  │
│  │   DAG: air_pipeline_daily                                 │  │
│  │                                                           │  │
│  │   ┌─────────────────────┐     ┌──────────────────────┐   │  │
│  │   │  Task 1             │     │  Task 2              │   │  │
│  │   │  fetch_weather_data │────▶│  insert_weather_data │   │  │
│  │   │                     │     │                      │   │  │
│  │   │  combine_data()     │     │  insert_data()       │   │  │
│  │   │  - Call OW API      │     │  - Connect Supabase  │   │  │
│  │   │  - Call AIR4Thai    │ XCom│  - INSERT to table   │   │  │
│  │   │  - Merge & clean    │     │    weather_data      │   │  │
│  │   └─────────────────────┘     └──────────────────────┘   │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Config: assets/.env  │  Logs: ./logs/                          │
└──────────────────────────────────────┬──────────────────────────┘
                                       │  Supabase Client (REST)
                                       ▼
                       ┌───────────────────────────┐
                       │        Supabase            │
                       │  (PostgreSQL Cloud DB)     │
                       │                            │
                       │  Table: weather_data       │
                       │  - datetime                │
                       │  - temperature, humidity   │
                       │  - wind_speed, wind_dir    │
                       │  - pressure, visibility    │
                       │  - cloud, sea_level        │
                       │  - temp_min, temp_max      │
                       │  - pm25                    │
                       │  - aqi                     │
                       │  - area, station_name      │
                       └───────────────────────────┘
```

## Getting Started

1. Clone the repository
2. Copy `assets/.env.example` to `assets/.env` and fill in your credentials
3. Run with Docker:

```bash
docker compose up
```

4. Open Airflow UI at `http://localhost:8080`

## AI Prediction

After collecting 3 months of data, I will train models and display results with visualizations in this repository.
