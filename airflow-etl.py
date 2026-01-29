from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from pipeline import main 

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5)}

with DAG(
    dag_id="binance_price_history_etl",
    default_args=default_args,
    description="Binance Data → SQL Server",
    schedule_interval="0 9 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["binance", "crypto"]
) as dag:

    run_binance_etl = PythonOperator(
        task_id="run_binance_etl",
        python_callable=main 
    )

    run_binance_etl
