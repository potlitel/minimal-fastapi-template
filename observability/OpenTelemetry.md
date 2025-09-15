# FastAPI Telemetry with OpenTelemetry 🚀

This project demonstrates sending different types of telemetry from FastAPI applications using OpenTelemetry to backend systems.

- [FastAPI Telemetry with OpenTelemetry 🚀](#fastapi-telemetry-with-opentelemetry-)
  - [Observability Stack Overview 🕵️‍♂️](#observability-stack-overview-️️)
  - [Summary of Service Functionalities ⚙️](#summary-of-service-functionalities-️)
    - [OpenTelemetry Collector 📡](#opentelemetry-collector-)
    - [Jaeger 🔍](#jaeger-)
    - [Prometheus 📊](#prometheus-)
    - [Loki 🗂️](#loki-️)
    - [Grafana 📈](#grafana-)
  - [How to Launch the Observability Stack Services 🚀🛠️](#how-to-launch-the-observability-stack-services-️)
  - [Conclusion 🏁](#conclusion-)
  
---

## Observability Stack Overview 🕵️‍♂️

In the **observability** folder, you'll find the `docker-compose.yml` file defining the services of the OpenTelemetry observability stack. The architecture is designed so that the OpenTelemetry Collector, here called **otel-collector**, acts as an intermediary receiving different telemetry types (traces, metrics, and logs) and forwarding them to the respective backend systems.

---

## Summary of Service Functionalities ⚙️

Below is a brief overview of each key service: OpenTelemetry Collector, Jaeger, Prometheus, Loki, and Grafana.

### OpenTelemetry Collector 📡

**Main Role:** Acts as a mediator to collect, process, and export telemetry data (traces, metrics, logs) from instrumented applications to different backends.

**Key Components:**

- **Receivers:** Accept telemetry data in various formats.
- **Processors:** Transform and filter data before forwarding.
- **Exporters:** Send processed data to target backends.

**Advantages:** Decouples instrumentation logic from apps, simplifies observability, and avoids needing multiple agents.

---

### Jaeger 🔍

**Main Role:** Distributed tracing platform for monitoring and troubleshooting microservice architectures.

**Features:**

- Monitoring distributed workflows.
- Identifying performance bottlenecks.
- Analyzing service dependencies.
- Trace visualization for debugging.

**How to View Traces in Jaeger?**

Once your application traces reach the Jaeger container, you can open the Jaeger UI at:

`http://localhost:16686`

- Use the search menu in the top left corner.
- Select your service name (e.g., `FastAPIApp`) in the dropdown. If it’s missing, traces may not have arrived yet.
- Choose specific operations (like HTTP endpoints `/items/{item_id}`) if desired.
- Set the time range (e.g., "Last 1 Hour").
- Click **Find Traces** to see the list.
- Click on any trace to view detailed spans, durations, and metadata—critical info for debugging bottlenecks and performance issues.

---

### Prometheus 📊

**Main Role:** Monitoring system and time-series database collecting app and system metrics.

**Features:**

- Multidimensional data model with named metrics and key-value pairs.
- Powerful PromQL query language for complex queries.
- Efficient storage and alerting based on defined conditions.

---

### Loki 🗂️

**Main Role:** Logs aggregation system enabling efficient log storage and querying.

**Features:**

- Built to integrate with Grafana for log visualization.
- Stores logs without indexing, reducing resource usage.
- Log querying with PromQL-like query language.

---

### Grafana 📈

**Main Role:** Data visualization and analytics platform for creating interactive dashboards to monitor metrics, logs, and traces.

**Features:**

- Multiple data sources support including Prometheus and Loki.
- Alerting tools for notifications via various channels.
- Customizable dashboards sharable among teams.
- Integration with incident and alert management tools.

---

## How to Launch the Observability Stack Services 🚀🛠️

The `docker-compose.yml` file is located in the root of this folder 🗂️ and defines all the services for the OpenTelemetry observability stack 📡.

To start all the services defined in this file, open a terminal 🖥️ in the root folder and run:


```bash
docker-compose up -d
```

where:

- The `up` command creates and starts the containers 🐳.
- The `-d` flag runs the containers in detached mode (in the background) 💤.
- This command will start all services including the OpenTelemetry Collector 📡, Jaeger 🔍, Prometheus 📊, Loki 🗂️, and Grafana 📈.

To stop the stack, run:

```bash
docker-compose down
```

This will stop and remove all the containers 🛑 created by the compose file but will preserve data volumes 💾 unless explicitly removed.

---

If you want to view logs from the running services, use:

```bash
docker-compose logs -f
```


This allows you to follow the logs in real time 📜⏳.

---

With these commands, you can easily launch 🚀, monitor 👀, and stop ⏹️ the full observability stack defined in the `docker-compose.yml` at the project root 📁.


## Conclusion 🏁

This set of services forms a robust observability stack enabling developers and operations teams to monitor, analyze, and optimize application and system performance effectively. Each service plays a specific role which, when integrated, provides comprehensive visibility into application health and behavior.
