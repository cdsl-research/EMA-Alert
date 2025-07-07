# EMA-Alert

## Features

- Dynamically calculates Exponential Moving Average (EMA) based thresholds from log data.
- Automatically updates ElastAlert rule files with new thresholds.
- Sends alerts to Slack if the threshold is exceeded.
- Tracks and logs EMA and threshold changes over time.
- Designed for log monitoring using Elasticsearch and ElastAlert2.

## Requirements

| Component        | Version             |
|------------------|----------------------|
| Nodes            | 1                    |
| Elasticsearch    | 8.13.4               |
| ElastAlert2      | 2.11.1               |
| Python           | 3.12.3               |
| PyYAML           | Latest (for YAML processing) |
| elasticsearch-py | Latest (for ES connection)   |

- This system uses **CDSL's Elasticsearch**.
- ElastAlert is set up using the [jertel/elastalert2](https://github.com/jertel/elastalert2) repository.

## Contents

| File          | Description |
|---------------|-------------|
| `warning.yaml`| ElastAlert rule with dynamic threshold |
| `ema.py`      | Python script to calculate and apply EMA threshold |
| `log.txt`     | Historical logs of EMA, standard deviation, and thresholds |
| `ema.txt`     | Historical EMA values for reference |
| `README.md`   | This documentation file |

### warning.yaml

This is the ElastAlert rule file. It defines when an alert should be triggered based on log frequency and updates dynamically with values set by `ema.py`.

```
type: frequency
num_events: 340
timeframe:
  minutes: 60
filter:
- term:
    log.syslog.severity.name.keyword: Warning
- term:
    host.hostname.keyword: lily
```

This rule checks for `Warning` severity logs from the host `lily` over a **1 hour** window. If the log count exceeds `num_events`, an alert is sent.

It sends a formatted alert to Slack using a webhook:

- Title: `⚠️ Dynamic Threshold Exceeded`
- Message: `*hostname* exceeded the dynamic log threshold in the last hour.`

A sample Slack alert image will be added in the final documentation.

### ema.py

This is the main script that handles:
- Connecting to Elasticsearch
- Fetching past 7 days of hourly logs
- Calculating EMA, standard deviation, and new threshold
- Updating the `warning.yaml` file
- Logging outputs

#### Example Cutouts & Explanations

1. **EMA Calculation Logic**

```
def calculate_ema(data, previous_ema=None, alpha=None):
    ...
    ema = alpha * x + (1 - alpha) * ema_values[-1]
```

This calculates the Exponential Moving Average based on incoming log counts.

2. **Threshold Computation**

```
ema = calculate_ema(counts, previous_ema=prev_ema)
stddev = statistics.stdev(counts[-N:])
threshold = ema + K * stddev
```

The final threshold is computed by adding standard deviation as a noise sensitivity factor.

3. **Updating YAML File**

```
rule["num_events"] = int(threshold)
yaml.dump(rule, f, sort_keys=False, allow_unicode=True)
```

This dynamically updates the `num_events` value inside the ElastAlert rule.

4. **Log Writing**

```
f.write(f"[{timestamp}] EMA: {ema:.2f}, StdDev: {stddev:.2f}, Threshold: {threshold:.2f}\n")
```

Writes the computed values to `log.txt` with timestamp.

5. **Elasticsearch Query**

```
"calendar_interval": "1h"
```

Log data is aggregated **per hour** for smoother trend tracking and EMA calculation.

#### k, n, time interval variables

These variables are manually set by me based on numerous experiments.

```
N = 3
K = 1.5
```

This means:
- `N = 3`: EMA is calculated using the last 3 data points.
- `K = 1.5`: Higher sensitivity to recent spikes in data.

And

```
"calendar_interval": "1h"
```

This means the script aggregates and evaluates logs every 1 hour. The EMA is also recalculated on an hourly basis.

### log.txt

This file logs the calculated values with timestamps for each run.

Example:

```
[2025-07-06T20:00:03.625647+00:00] EMA: 117.67, StdDev: 171.24, Threshold: 340.29
```

It is generated and appended by `ema.py` during every execution.

### ema.txt

This file stores only the EMA values used for continuity.

Example:

```
[2025-07-06T20:00:03.621150+00:00] EMA: 117.67
```

This helps the system calculate future EMA values by using the latest one.

## example of execution

(To be written by the author)

## Conclusion

This system enables dynamic threshold alerting based on real-time and historical log patterns. By applying EMA and adjusting sensitivity with standard deviation, the system reduces false alerts and adapts to log fluctuations automatically. It is suitable for environments with variable load where static thresholds are ineffective.
