# Real-Time Data Engineering Pipeline  
**Kafka • Airflow • Spark Structured Streaming • Cassandra • Docker**

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Airflow](https://img.shields.io/badge/Airflow-2.9-green.svg)
![Kafka](https://img.shields.io/badge/Kafka-Confluent_7.9-black.svg)
![Spark](https://img.shields.io/badge/Spark-3.5-orange.svg)
![Cassandra](https://img.shields.io/badge/Cassandra-4.1-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)

This project is an end-to-end **real-time data engineering pipeline** built with:

- **Airflow** – orchestrates and schedules data ingestion  
- **Kafka** – message broker for streaming events  
- **Spark Structured Streaming** – real-time processing engine  
- **Cassandra** – scalable analytical storage  
- **Postgres** – Airflow metadata database  
- **Docker Compose** – single-command local infrastructure  

---

## Architecture Overview

<img width="1713" height="722" alt="image" src="https://github.com/user-attachments/assets/1e898da1-c0ee-4b1a-8cd4-65b7f8aa9fc1" />

The pipeline looks like this:

```mermaid
flowchart LR
    subgraph Orchestration [Orchestration: Airflow + Postgres]
        A[Airflow Webserver<br/>Airflow Scheduler]
        B[(Postgres<br/>Airflow Metadata DB)]
        A <--> B
    end

    subgraph Ingestion [Data Ingestion]
        API[RandomUser API]
        K[Kafka Topic<br/>users_created]
    end

    subgraph Processing [Streaming Processing]
        S[Spark Structured Streaming Job]
    end

    subgraph Storage [Analytics Storage]
        C[(Cassandra<br/>spark_streams.created_users)]
    end

    A -->|DAG user_automation| API
    API --> K
    K --> S
    S --> C
````

**Flow:**

1. Airflow DAG `user_automation` periodically calls the public API `https://randomuser.me/api/`.
2. API responses are normalized to a clean JSON schema.
3. Records are sent to **Kafka** topic `users_created`.
4. **Spark Structured Streaming** subscribes to the topic and parses JSON into a structured DataFrame.
5. Parsed events are written into **Cassandra** table `spark_streams.created_users` for analytics.

---

## Tech Stack

| Layer            | Technologies                                                |
| ---------------- | ----------------------------------------------------------- |
| Orchestration    | Apache Airflow 2.9, Postgres 17                             |
| Streaming Broker | Kafka (Confluent cp-server 7.9, KRaft, Schema Registry, C3) |
| Processing       | Spark 3.5 Structured Streaming                              |
| Storage          | Cassandra 4.1                                               |
| Containerization | Docker, Docker Compose v2                                   |
| Languages        | Python 3.11, PySpark                                        |

---

## Project Structure

```bash
.
├── dags/
│   └── kafka_stream.py
├── script/
│   └── spark_stream.py
├── docker-compose.yml
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Components in Detail

### 1️⃣ Airflow DAG: `user_automation`

File: `dags/kafka_stream.py`

Responsibilities:

* calls `https://randomuser.me/api/`
* extracts and normalizes user attributes
* publishes messages to Kafka topic `users_created`
* handles retries and API errors

Idea: treat each user as an event with a stable JSON schema and stream it into Kafka.

---

### 2️⃣ Kafka & Schema Registry

* Single-node Kafka in **KRaft mode** (no Zookeeper)
* Pre-created topic: `users_created`
* Integrated with Confluent Control Center

Useful commands:

```bash
# List topics
docker compose exec broker kafka-topics \
  --bootstrap-server broker:29092 --list

# Peek into the stream
docker compose exec broker kafka-console-consumer \
  --bootstrap-server broker:29092 \
  --topic users_created \
  --from-beginning \
  --max-messages 5
```

Control Center UI: **[http://localhost:9021/](http://localhost:9021/)**

---

### 3️⃣ Spark Streaming Job

File: `script/spark_stream.py`

Responsibilities:

* read from Kafka:

  ```python
  spark.readStream.format("kafka") \
       .option("kafka.bootstrap.servers", "broker:29092") \
       .option("subscribe", "users_created")
  ```

* parse JSON payloads into a structured schema (id, name, email, address, gender, etc.)

* write the resulting stream to Cassandra:

  ```python
  selection_df.writeStream \
      .format("org.apache.spark.sql.cassandra") \
      .option("keyspace", "spark_streams") \
      .option("table", "created_users") \
      .outputMode("append") \
      .start()
  ```

Spark Master UI: **[http://localhost:9090/](http://localhost:9090/)**

---

### 4️⃣ Cassandra

* Keyspace: `spark_streams`
* Table: `created_users`

Example queries:

```bash
docker exec -it cassandra cqlsh
```

```sql
DESCRIBE KEYSPACES;
USE spark_streams;
DESCRIBE TABLES;

SELECT count(*) FROM created_users;

SELECT id, first_name, last_name, email
FROM created_users
LIMIT 5;
```

This table can be used as a base for analytical workloads or as a source layer for downstream batch jobs.

---

### 5️⃣ Postgres (Airflow Metadata)

Postgres is used **only by Airflow** to store:

* DAG definitions and runs
* task instances
* logs & scheduling metadata

It does **not** store domain data — all business data flows Kafka → Spark → Cassandra.
However, without Postgres, Airflow cannot function — so it's a critical part of orchestration.

---

## Getting Started

> Requires Docker Desktop and Docker Compose v2+.

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/data-engineering.git
cd data-engineering
```

### 2. Start the full stack

```bash
docker compose up -d
```

Check the containers:

```bash
docker compose ps
```

### 3. Access UIs

* **Airflow Web UI** – [http://localhost:8080/](http://localhost:8080/)
* **Kafka Control Center** – [http://localhost:9021/](http://localhost:9021/)
* **Spark Master UI** – [http://localhost:9090/](http://localhost:9090/)

---

## Running the Pipeline

### Step 1 — Log in to Airflow

By default, an admin user is created via CLI:

```bash
docker compose exec webserver airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com
```

Then:

1. Go to [http://localhost:8080/](http://localhost:8080/)
2. Log in with `admin / admin`
3. Enable DAG `user_automation`
4. Trigger it manually or wait for the schedule

---

### Step 2 — Verify Kafka

```bash
docker compose exec broker kafka-console-consumer \
  --bootstrap-server broker:29092 \
  --topic users_created \
  --from-beginning \
  --max-messages 5
```

You should see JSON messages coming from the RandomUser API.

---

### Step 3 — Verify Cassandra

```bash
docker exec -it cassandra cqlsh
USE spark_streams;

SELECT count(*) FROM created_users;
SELECT id, first_name, last_name, email FROM created_users LIMIT 5;
```

If you see rows — your real-time pipeline is alive

---

## Example Output

```text
 id                                   | first_name | last_name   | email
--------------------------------------+------------+-------------+------------------------------
 2df92f01-3da1-4090-a2f1-921e87e8256f | Efe        | Erbulak     | efe.erbulak@example.com
 0cbd5606-49a4-4e7d-91b8-5c592d48ba9f | Gabin      | Nicolas     | gabin.nicolas@example.com
 ...
```
