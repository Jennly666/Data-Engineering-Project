import uuid
from datetime import datetime, timezone
from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {
    "owner": "petproject",
    "start_date": datetime(2023, 9, 3, 10, 0, tzinfo=timezone.utc),
}


def get_data():
    import requests
    res = requests.get("https://randomuser.me/api/", timeout=15)
    res.raise_for_status()
    return res.json()["results"][0]


def format_data(res):
    location = res["location"]
    return {
        "id": str(uuid.uuid4()),  # JSON-friendly
        "first_name": res["name"]["first"],
        "last_name": res["name"]["last"],
        "gender": res["gender"],
        "address": f"{location['street']['number']} {location['street']['name']}, "
                   f"{location['city']}, {location['state']}, {location['country']}",
        "post_code": str(location["postcode"]),
        "email": res["email"],
        "username": res["login"]["username"],
        "dob": res["dob"]["date"],
        "registered_date": res["registered"]["date"],
        "phone": res["phone"],
        "picture": res["picture"]["medium"],
    }


def stream_data():
    import json, time, logging
    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers=["broker:29092"],
        max_block_ms=5000,
    )
    stop_at = time.time() + 60

    while time.time() <= stop_at:
        try:
            payload = format_data(get_data())
            producer.send("users_created", json.dumps(payload).encode("utf-8"))
            time.sleep(0.5)
        except Exception:
            logging.exception("stream_data error")
            time.sleep(1)


with DAG(
    dag_id="user_automation",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
) as dag:
    streaming_task = PythonOperator(
        task_id="stream_data_from_api",
        python_callable=stream_data,
    )
