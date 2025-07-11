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

## Example of execution
### 1. Cronjob Execution
First of all, set up a cronjob to execute ema.py hourly, so that the threshold will change by the hour.
```terminal
(elast2) c0a22173@elast:~/elastalert2/ema$ crontab -e
crontab: installing new crontab
(elast2) c0a22173@elast:~/elastalert2/ema$ crontab -l
0 * * * * /home/c0a22173/elastalert2/ema/ema.py >> /home/c0a22173/elastalert2/ema/cron.log 2>&1
```

### 2. Elastalert execution
Now, set up Elastalert so that it will keep on running eventhough the terminal is closed, so that it can still monitor the logs.

Command to run Elastalert with nohup.
```
nohup elastalert --config config.yaml --rule rules1/warning.yaml --verbose --es_debug > elastalert.log 2>&1 &
```

Command to check the Elastalert logs
```
tail -f elastalert.log
```

Command to check if elastalert is running
```
ps aux | grep elastalert
```

Command to kill Elastalert (ID can be obtained through the previous command)
```
kill <ID>
```

#### Elastalert example Execution
```
c0a22173@elast:~/elastalert2$ nohup elastalert --config config.yaml --rule rules1/warning.yaml --verbose --es_debug > elastalert.log 2>&1 &
[1] 3016
c0a22173@elast:~/elastalert2$ tail -f elastalert.log
nohup: ignoring input
INFO:elastalert:1 rules loaded
INFO:elastalert:Starting up
INFO:elastalert:Disabled rules are: []
INFO:elastalert:Sleeping for 59.99995 seconds
INFO:elastalert:Ran Dynamic Threshold for Warning Logs from 2025-07-01 01:34 UTC to 2025-07-01 01:35 UTC: 0 query hits (0 already seen), 0 matches, 0 alerts sent
INFO:elastalert:Dynamic Threshold for Warning Logs range 32
^C
c0a22173@elast:~/elastalert2$ ps aux | grep elastalert
c0a22173    3016  1.6  0.8 228320 66760 pts/0    Sl   01:35   0:00 /home/c0a22173/elast2/bin/python3 /home/c0a22173/elast2/bin/elastalert --config config.yaml --rule rules1/warning.yaml --verbose --es_debug
c0a22173    3023  0.0  0.0   6544  2304 pts/0    S+   01:35   0:00 grep --color=auto elastalert
c0a22173@elast:~/elastalert2$ kill 3016
c0a22173@elast:~/elastalert2$ ps aux | grep elastalert
c0a22173    3025  0.0  0.0   6544  2304 pts/0    S+   01:36   0:00 grep --color=auto elastalert
[1]+  Terminated              nohup elastalert --config config.yaml --rule rules1/warning.yaml --verbose --es_debug > elastalert.log 2>&1
```

### Final Execution
- ema.py Execution.  
![image](https://github.com/user-attachments/assets/2157061f-fb00-4691-bab1-4662bcf2e012)

- ema.py txt files   
ema.txt  
![image](https://github.com/user-attachments/assets/59e91bd4-28b6-46f8-8c2d-e63a1a31c3d5)  
log.txt  
![image](https://github.com/user-attachments/assets/788aa900-8de2-4df5-8700-22fc23f45f4d)  

- Elastalert logs  
![image](https://github.com/user-attachments/assets/7c6d477d-7a1d-443a-9503-d08b7bc37c77)

- Slack Alert Message   
![image](https://github.com/user-attachments/assets/6c96d0b8-6193-4fc6-a203-4b61df0a3be0)   

## Conclusion

This system enables dynamic threshold alerting based on real-time and historical log patterns. By applying EMA and adjusting sensitivity with standard deviation, the system reduces false alerts and adapts to log fluctuations automatically. It is suitable for environments with variable load where static thresholds are ineffective.
