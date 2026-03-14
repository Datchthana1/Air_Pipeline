from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.timetables.interval import CronDataIntervalTimetable
from airflow.models.param import Param
from datetime import timedelta
from function import insert_daily_data, process_daily_data
from datetime import date
import pendulum

local_tz = pendulum.timezone("Asia/Bangkok")

default_args = {
    "owner": "air_pipeline",
    "depends_on_past": False,
    "start_date": pendulum.datetime(2024, 6, 1, tz=local_tz),
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}


def process_data_daily(**context):
    params = context["params"]
    target_date = params["target_date"]
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)
    print(f"Processing data for date: {target_date}")
    records = process_daily_data(target_date)
    return insert_daily_data(records, "weather_data_daily") if records else None


with DAG(
    dag_id="air_pipeline_daily",
    default_args=default_args,
    schedule=CronDataIntervalTimetable(
        cron="0 0 * * *", timezone=pendulum.timezone("Asia/Bangkok")
    ),
    catchup=False,
    params={
        "target_date": Param(default=None),
    },
) as dag_daily:

    task_process_daily = PythonOperator(
        task_id="process_data_daily",
        python_callable=process_data_daily,
    )
