# cronwatcher

> Lightweight daemon that monitors cron job execution, logs failures, and sends configurable alerts.

---

## Installation

```bash
pip install cronwatcher
```

Or install from source:

```bash
git clone https://github.com/youruser/cronwatcher.git && cd cronwatcher && pip install .
```

---

## Usage

Start the daemon with a configuration file:

```bash
cronwatcher start --config /etc/cronwatcher/config.yaml
```

Example `config.yaml`:

```yaml
jobs:
  - name: daily-backup
    schedule: "0 2 * * *"
    command: /usr/local/bin/backup.sh
    timeout: 3600
    alert_on_failure: true

alerts:
  email:
    to: ops@example.com
    from: cronwatcher@example.com
    smtp_host: smtp.example.com
  slack:
    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL

log:
  path: /var/log/cronwatcher.log
  level: info
```

Stop the daemon:

```bash
cronwatcher stop
```

View recent job history:

```bash
cronwatcher status
```

---

## License

This project is licensed under the [MIT License](LICENSE).