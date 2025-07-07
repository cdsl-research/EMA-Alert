#!/home/c0a22173/elast2/bin/python3
import os
import statistics
from elasticsearch import Elasticsearch
from datetime import datetime, timezone, timedelta
import yaml

# === Configuration ===
ES_HOST = "ls-master.a910.tak-cslab.org"
ES_PORT = 30092
INDEX = "syslog-*"
SEVERITY = "Warning"
HOSTS = ["lily"]  # ← now tracking lily only
N = 3
K = 1.5

# === Absolute Paths ===
BASE_DIR = "/home/c0a22173/elastalert2"
YAML_RULE_PATH = f"{BASE_DIR}/rules1/warning.yaml"
EMA_FILE = f"{BASE_DIR}/ema/ema.txt"
LOG_FILE = f"{BASE_DIR}/ema/log.txt"
LOOKBACK_HOURS = 24 * 7  # 7 days

# === EMA Calculation ===
def calculate_ema(data, previous_ema=None, alpha=None):
    if not data:
        return None
    if alpha is None:
        alpha = 2 / (N + 1)
    ema_values = []
    for i, x in enumerate(data):
        if i == 0 and previous_ema is None:
            ema = x
        elif i == 0:
            ema = alpha * x + (1 - alpha) * previous_ema
        else:
            ema = alpha * x + (1 - alpha) * ema_values[-1]
        ema_values.append(ema)
    return ema_values[-1] if ema_values else None

# === Fetch Hourly Log Counts ===
def fetch_log_counts():
    es = Elasticsearch(
        hosts=[{"host": ES_HOST, "port": ES_PORT}],
        timeout=30,
        request_timeout=30
    )
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=LOOKBACK_HOURS)
    query = {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"range": {"@timestamp": {"gte": start_time.isoformat(), "lt": end_time.isoformat()}}},
                    {"term": {"log.syslog.severity.name.keyword": SEVERITY}},
                    {"terms": {"host.hostname.keyword": HOSTS}}
                ]
            }
        },
        "aggs": {
            "per_hour": {
                "date_histogram": {
                    "field": "@timestamp",
                    "calendar_interval": "1h"
                }
            }
        }
    }
    response = es.search(index=INDEX, body=query)
    buckets = response.get("aggregations", {}).get("per_hour", {}).get("buckets", [])
    return [bucket["doc_count"] for bucket in buckets]

# === Read Last EMA (for smooth continuation) ===
def load_last_ema():
    if not os.path.exists(EMA_FILE):
        return None
    with open(EMA_FILE, "r") as f:
        try:
            lines = f.readlines()
            if not lines:
                return None
            last_line = lines[-1]
            return float(last_line.split("EMA:")[1].strip())
        except:
            return None

# === Save EMA (Append Mode with Timestamp) ===
def save_ema(value):
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(EMA_FILE, "a") as f:
        f.write(f"[{timestamp}] EMA: {value:.2f}\n")

# === Update YAML File with dynamic threshold ===
def update_yaml(threshold):
    with open(YAML_RULE_PATH, "r") as f:
        rule = yaml.safe_load(f)
    rule["num_events"] = int(threshold)  # dynamic threshold
    with open(YAML_RULE_PATH, "w") as f:
        yaml.dump(rule, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

# === Optional Logging for Debugging ===
def log_update(ema, stddev, threshold):
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.now(timezone.utc).isoformat()
        f.write(f"[{timestamp}] EMA: {ema:.2f}, StdDev: {stddev:.2f}, Threshold: {threshold:.2f}\n")

# === Main Function ===
def main():
    print("Fetching log data from Elasticsearch...")
    counts = fetch_log_counts()

    if len(counts) < N:
        print("Not enough data to calculate EMA.")
        return

    prev_ema = load_last_ema()
    ema = calculate_ema(counts, previous_ema=prev_ema)
    stddev = statistics.stdev(counts[-N:])
    threshold = ema + K * stddev

    save_ema(ema)
    update_yaml(threshold)
    log_update(ema, stddev, threshold)
    print(f"Updated threshold: {threshold:.2f}")

if __name__ == "__main__":
    main()
