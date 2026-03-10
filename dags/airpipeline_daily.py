from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.timetables.interval import CronDataIntervalTimetable
from airflow.models.param import Param
from datetime import timedelta
from function import insert_daily_data, process_daily_data
import pendulum

local_tz = pendulum.timezone("Asia/Bangkok")

default_args = {
    "owner": "air_pipeline",
    "depends_on_past": False,
    "start_date": pendulum.datetime(2024, 6, 1, tz=local_tz),
    "retries": 1,
    # "retry_delay": timedelta(minutes=2),
}


def process_data_daily():
    records = process_daily_data()
    return insert_daily_data(records, "weather_data_daily") if records else None


with DAG(
    dag_id="air_pipeline_daily",
    default_args=default_args,
    schedule=CronDataIntervalTimetable(
        cron="0 0 * * *", timezone=pendulum.timezone("Asia/Bangkok")
    ),
    catchup=False,
) as dag_daily:

    task_process_daily = PythonOperator(
        task_id="process_data_daily",
        python_callable=process_data_daily,
    )
