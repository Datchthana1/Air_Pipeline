from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models.param import Param
from datetime import timedelta
from function import combine_data, insert_data, LAT, LON, OW_API, STATION_ID
import os
import pendulum

local_tz = pendulum.timezone("Asia/Bangkok")

default_args = {
    'owner': 'air_pipeline',
    'depends_on_past': False,
    'start_date': pendulum.datetime(2024, 6, 1, tz=local_tz),
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
}

def fetch_weather(**context):
    params = context["params"]
    data = combine_data(
        params["lat"],
        params["lon"],
        OW_API,
        params["station_id"],
    )
    return data

def insert_weather(**context):
    data = context['ti'].xcom_pull(task_ids='fetch_weather_data')
    return insert_data(data)

with DAG(
    dag_id='air_pipeline_daily',
    default_args=default_args,
    schedule_interval='0 * * * *',
    catchup=False,
    params={
        "lat": Param(default=LAT, type="string"),
        "lon": Param(default=LON, type="string"),
        "station_id": Param(default=STATION_ID, type="string"),
    }
) as dag:

    task_fetch = PythonOperator(
        task_id='fetch_weather_data',
        python_callable=fetch_weather,
    )

    task_process = PythonOperator(
        task_id='insert_weather_data',
        python_callable=insert_weather,
    )

    task_fetch >> task_process
