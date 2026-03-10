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
## System Architecture

┌──────────────────────────────────────────────────────────────────────┐
│                          External APIs                               │
│                                                                      │
│  ┌───────────────────────────┐    ┌─────────────────────────────┐   │
│  │    OpenWeatherMap API     │    │     AIR4Thai API (PCD)      │   │
│  │  api.openweathermap.org   │    │   air4thai.pcd.go.th        │   │
│  │                           │    │   Station ID: o10           │   │
│  │  - Temperature            │    │                             │   │
│  │  - Humidity               │    │   - PM2.5                   │   │
│  │  - Wind Speed / Direction │    │   - AQI                     │   │
│  │  - Pressure               │    │   - Area / Station Name     │   │
│  │  - Visibility             │    │                             │   │
│  │  - Cloud Description      │    └──────────────┬──────────────┘   │
│  │  - Sea Level              │                   │                  │
│  │  - Temp Min / Max         │                   │                  │
│  └──────────────┬────────────┘                   │                  │
│                 │                                │                  │
└─────────────────┼────────────────────────────────┼──────────────────┘
                  │  HTTP GET                      │  HTTP GET
                  └───────────────┬────────────────┘
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Docker Container (Airflow Standalone)             │
│                                                                      │
│  Volumes:  ./dags      → /opt/airflow/dags                          │
│            ./logs      → /opt/airflow/logs                          │
│            ./assets/.env → /opt/airflow/assets/.env                 │
│  Port: 8080                                                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  DAG: air_pipeline_hourly  (cron: 0 * * * * | Asia/Bangkok)   │ │
│  │                                                                │ │
│  │  ┌──────────────────────┐  XCom  ┌───────────────────────┐   │ │
│  │  │  Task 1              │ ──────▶│  Task 2               │   │ │
│  │  │  fetch_weather_data  │        │  insert_weather_data  │   │ │
│  │  │                      │        │                       │   │ │
│  │  │  combine_data()      │        │  insert_data()        │   │ │
│  │  │  - Call OW API       │        │  - Connect Supabase   │   │ │
│  │  │  - Call AIR4Thai     │        │  - INSERT 1 row →     │   │ │
│  │  │  - Merge fields      │        │    weather_data       │   │ │
│  │  │  retries: 3 (2 min)  │        │                       │   │ │
│  │  └──────────────────────┘        └───────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  DAG: air_pipeline_daily   (cron: 0 0 * * * | Asia/Bangkok)   │ │
│  │                                                                │ │
│  │  ┌─────────────────────────────────────────────────────────┐  │ │
│  │  │  Task 1                                                 │  │ │
│  │  │  process_data_daily                                     │  │ │
│  │  │                                                         │  │ │
│  │  │  process_daily_data()   → Read yesterday's rows from    │  │ │
│  │  │                            weather_data (24 rows)       │  │ │
│  │  │                         → Aggregate via pandas resample │  │ │
│  │  │                           (mean / min / max / mode)     │  │ │
│  │  │  insert_daily_data()    → INSERT 1 row →                │  │ │
│  │  │                            weather_data_daily           │  │ │
│  │  │  retries: 1                                             │  │ │
│  │  └─────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │  Supabase Client (REST / HTTPS)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Supabase (PostgreSQL Cloud)                       │
│                                                                      │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐  │
│  │  Table: weather_data        │  │  Table: weather_data_daily   │  │
│  │  (raw · 1 row/hour)         │  │  (aggregated · 1 row/day)    │  │
│  │                             │  │                              │  │
│  │  - datetime                 │  │  - datetime                  │  │
│  │  - temperature              │  │  - temperature (mean)        │  │
│  │  - humidity                 │  │  - humidity (mean)           │  │
│  │  - wind_speed               │  │  - wind_speed (mean)         │  │
│  │  - wind_direction           │  │  - wind_direction (mode)     │  │
│  │  - pressure                 │  │  - pressure (mean)           │  │
│  │  - visibility               │  │  - visibility (mean)         │  │
│  │  - cloud                    │  │  - cloud (mode)              │  │
│  │  - sea_level                │  │  - sea_level (mean)          │  │
│  │  - temp_min                 │  │  - temp_min (min)            │  │
│  │  - temp_max                 │  │  - temp_max (max)            │  │
│  │  - pm25                     │  │  - pm25 (mean)               │  │
│  │  - aqi                      │  │  - aqi (mean)                │  │
│  │  - area                     │  │  - area (mode)               │  │
│  │  - station_name             │  │  - station_name (mode)       │  │
│  └─────────────────────────────┘  └──────────────────────────────┘  │
│                    ▲                            ▲                    │
│                    │  write (hourly)            │  write (midnight)  │
│         air_pipeline_hourly          air_pipeline_daily              │
│                                      reads FROM weather_data         │
└──────────────────────────────────────────────────────────────────────┘
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
