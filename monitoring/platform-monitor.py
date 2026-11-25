#!/usr/bin/env python3
"""Periodic platform reliability checks; uses only Python's standard library."""
import base64
import json
import os
import smtplib
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
import shutil

STATE_DIR = Path(os.getenv("MONITOR_STATE_DIR", "/state"))
STATE_FILE = STATE_DIR / "monitor-state.json"
INTERVAL = max(60, int(os.getenv("MONITOR_INTERVAL_SECONDS", "900")))
TIMEOUT = max(3, int(os.getenv("MONITOR_TIMEOUT_SECONDS", "12")))

def utcnow():
    return datetime.now(timezone.utc)

def request(url, method="GET", headers=None, data=None, timeout=TIMEOUT):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(1024 * 1024)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(1024 * 1024)

def tls_check(host):
    host = host.strip()
    if not host:
        return None
    port = 443
    if ":" in host and host.count(":") == 1:
        host, raw_port = host.rsplit(":", 1); port = int(raw_port)
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
        with context.wrap_socket(sock, server_hostname=host) as secure:
            cert = secure.getpeercert()
    expiry = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    days = (expiry - utcnow()).days
    return {"status": "ok" if days > 14 else "warning" if days > 7 else "critical",
            "expires_at": expiry.isoformat(), "days_remaining": days}

def domain_check(domain):
    domain = domain.strip().lower()
    if not domain:
        return None
    code, body = request("https://rdap.org/domain/" + urllib.parse.quote(domain))
    if code != 200:
        raise RuntimeError(f"RDAP lookup returned HTTP {code}")
    record = json.loads(body)
    expiration = next((event.get("eventDate") for event in record.get("events", [])
                       if event.get("eventAction", "").lower() in ("expiration", "expiry")), None)
    if not expiration:
        raise RuntimeError("RDAP response did not include a domain expiration event")
    expiry = datetime.fromisoformat(expiration.replace("Z", "+00:00"))
    days = (expiry - utcnow()).days
    return {"status": "ok" if days > 30 else "warning" if days > 14 else "critical",
            "expires_at": expiry.isoformat(), "days_remaining": days}

def app_health_check():
    base = os.getenv("MONITOR_APP_URL", "").rstrip("/")
    if not base:
        raise RuntimeError("MONITOR_APP_URL is not configured")
    code, body = request(base + "/api/health")
    if code != 200:
        raise RuntimeError(f"Application health endpoint returned HTTP {code}")
    try:
        payload = json.loads(body)
    except ValueError:
        payload = {}
    return {"status": "ok", "http_status": code, "database": payload.get("database", "reported by API")}

def smtp_check():
    host = os.getenv("SMTP_HOST", "").strip()
    if not host:
        raise RuntimeError("SMTP_HOST is not configured")
    port = int(os.getenv("SMTP_PORT", "587"))
    user, password = os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD")
    if os.getenv("SMTP_USE_SSL", "false").lower() == "true":
        client = smtplib.SMTP_SSL(host, port, timeout=TIMEOUT, context=ssl.create_default_context())
    else:
        client = smtplib.SMTP(host, port, timeout=TIMEOUT)
    with client:
        client.ehlo()
        if os.getenv("SMTP_USE_TLS", "true").lower() == "true" and not isinstance(client, smtplib.SMTP_SSL):
            client.starttls(context=ssl.create_default_context()); client.ehlo()
        if user and password:
            client.login(user, password)
        return {"status": "ok", "host": host, "port": port, "authenticated": bool(user and password)}

def send_email(subject, body, recipient=None):
    recipient = recipient or os.getenv("MONITOR_ALERT_EMAIL", "")
    sender = os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USERNAME", "")
    if not recipient or not sender:
        raise RuntimeError("MONITOR_ALERT_EMAIL and SMTP_FROM_EMAIL (or SMTP_USERNAME) are required")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender, recipient
    msg.set_content(body)
    host, port = os.getenv("SMTP_HOST", ""), int(os.getenv("SMTP_PORT", "587"))
    if os.getenv("SMTP_USE_SSL", "false").lower() == "true":
        with smtplib.SMTP_SSL(host, port, timeout=TIMEOUT, context=ssl.create_default_context()) as client:
            if os.getenv("SMTP_USERNAME") and os.getenv("SMTP_PASSWORD"):
                client.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
            client.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=TIMEOUT) as client:
            client.ehlo()
            if os.getenv("SMTP_USE_TLS", "true").lower() == "true":
                client.starttls(context=ssl.create_default_context()); client.ehlo()
            if os.getenv("SMTP_USERNAME") and os.getenv("SMTP_PASSWORD"):
                client.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
            client.send_message(msg)

def razorpay_check():
    key, secret = os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")
    if not key or not secret:
        raise RuntimeError("Razorpay API credentials are not configured")
    token = base64.b64encode((key + ":" + secret).encode()).decode()
    code, _ = request("https://api.razorpay.com/v1/payments?count=1",
                      headers={"Authorization": "Basic " + token})
    if code != 200:
        raise RuntimeError(f"Razorpay API returned HTTP {code}")
    return {"status": "ok", "http_status": code}

def webhook_check():
    base = os.getenv("MONITOR_APP_URL", "").rstrip("/")
    if not base:
        raise RuntimeError("MONITOR_APP_URL is not configured")
    url = base + "/api/platform/ops/payments/webhook"
    code, _ = request(url, method="POST",
                      headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid-monitor-probe"},
                      data=b"{}")
    # The webhook handler validates HMAC before parsing or mutating payment state.
    if code != 400:
        raise RuntimeError(f"Webhook signature-rejection probe expected HTTP 400, got HTTP {code}")
    return {"status": "ok", "endpoint_reachable": True, "signature_validation_enforced": True}

def classify_transitions(previous, current):
    failures = {k: v for k, v in current.items()
                if isinstance(v, dict) and v.get("status") in ("critical", "warning")}
    old_failures = previous.get("failures", {})
    new_failures = {k: v for k, v in failures.items() if k not in old_failures}
    recovered = [k for k in old_failures if k not in failures]
    return failures, new_failures, recovered

def overall_status(results):
    states = [v.get("status") for v in results.values() if isinstance(v, dict)]
    if "critical" in states: return "critical"
    if "warning" in states: return "warning"
    if "not_configured" in states: return "partial"
    return "healthy"

def _read_meminfo(path):
    values = {}
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
    total, available = values.get("MemTotal", 0), values.get("MemAvailable", 0)
    return round((total - available) / total * 100, 1) if total else None

def host_metrics():
    proc = Path("/host/proc")
    root = Path("/host/root")
    metrics = {}
    try:
        metrics["memory_used_percent"] = _read_meminfo(proc / "meminfo")
    except (OSError, ValueError, KeyError):
        metrics["memory_used_percent"] = None
    try:
        load = [float(x) for x in (proc / "loadavg").read_text().split()[:3]]
        cpu_count = max(1, len((proc / "stat").read_text().splitlines()[0:1]) and
                        sum(1 for line in (proc / "stat").read_text().splitlines() if line.startswith("cpu") and line[3:4].isdigit()))
        metrics["cpu_load_average"] = load
        metrics["cpu_load_per_core"] = round(load[0] / max(1, cpu_count), 2)
    except (OSError, ValueError):
        metrics["cpu_load_average"] = None
        metrics["cpu_load_per_core"] = None
    try:
        disk = shutil.disk_usage(root)
        metrics["host_disk_used_percent"] = round(disk.used / disk.total * 100, 1)
    except OSError:
        metrics["host_disk_used_percent"] = None
    try:
        disk = shutil.disk_usage("/backups")
        metrics["backup_disk_used_percent"] = round(disk.used / disk.total * 100, 1)
        metrics["backup_disk_free_bytes"] = disk.free
    except OSError:
        metrics["backup_disk_used_percent"] = None
        metrics["backup_disk_free_bytes"] = None
    return metrics

def apply_resource_thresholds(results, metrics):
    warning_disk = float(os.getenv("MONITOR_DISK_WARNING_PERCENT", "80"))
    critical_disk = float(os.getenv("MONITOR_DISK_CRITICAL_PERCENT", "90"))
    warning_mem = float(os.getenv("MONITOR_MEMORY_WARNING_PERCENT", "85"))
    critical_mem = float(os.getenv("MONITOR_MEMORY_CRITICAL_PERCENT", "95"))
    warning_cpu = float(os.getenv("MONITOR_CPU_LOAD_PER_CORE_WARNING", "1.5"))
    critical_cpu = float(os.getenv("MONITOR_CPU_LOAD_PER_CORE_CRITICAL", "3.0"))
    for name, value, warn, critical in (
        ("host_disk", metrics.get("host_disk_used_percent"), warning_disk, critical_disk),
        ("backup_disk", metrics.get("backup_disk_used_percent"), warning_disk, critical_disk),
        ("host_memory", metrics.get("memory_used_percent"), warning_mem, critical_mem),
        ("host_cpu_load", metrics.get("cpu_load_per_core"), warning_cpu, critical_cpu),
    ):
        if value is None:
            results[name] = {"status": "unavailable"}
        else:
            state = "critical" if value >= critical else "warning" if value >= warn else "ok"
            results[name] = {"status": state, "value": value}
    return results

def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}

def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2))
    temp.replace(STATE_FILE)

def backup_status():
    path = Path("/backups/backup-status.json")
    try:
        status = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"status": "not_configured"}
    if status.get("offsite_status") == "failed":
        return {"status": "critical", "reason": status.get("offsite_error", "offsite verification failed")}
    if os.getenv("BACKUP_S3_URI") and status.get("offsite_status") != "restore_verified":
        return {"status": "warning", "reason": "offsite copy is not independently restore-verified"}
    if status.get("restore_verified") is not True:
        return {"status": "critical", "reason": "latest local archive has not passed restore verification"}
    return {"status": "ok", "archive": status.get("archive"), "offsite_status": status.get("offsite_status", "not_configured")}

def run_checks():
    results = {}
    for host in filter(None, os.getenv("MONITOR_TLS_HOSTS", "").split(",")):
        key = "tls:" + host.strip()
        try: results[key] = tls_check(host)
        except Exception as exc: results[key] = {"status": "critical", "error": str(exc)}
    for domain in filter(None, os.getenv("MONITOR_DOMAINS", "").split(",")):
        key = "domain:" + domain.strip()
        try: results[key] = domain_check(domain)
        except Exception as exc: results[key] = {"status": "critical", "error": str(exc)}
    for key, fn in (("application", app_health_check), ("smtp", smtp_check), ("razorpay_api", razorpay_check), ("razorpay_webhook", webhook_check)):
        enabled = {"application": bool(os.getenv("MONITOR_APP_URL")), "smtp": bool(os.getenv("SMTP_HOST")), "razorpay_api": bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET")), "razorpay_webhook": bool(os.getenv("MONITOR_APP_URL"))}[key]
        if not enabled:
            results[key] = {"status": "not_configured"}
            continue
        try: results[key] = fn()
        except Exception as exc: results[key] = {"status": "critical", "error": str(exc)}
    metrics = host_metrics()
    apply_resource_thresholds(results, metrics)
    results["host_metrics"] = metrics
    results["backup"] = backup_status()
    results["checked_at"] = utcnow().isoformat()
    return results

def main():
    previous = load_state()
    while True:
        current = run_checks()
        failures = {k: v for k, v in current.items()
                    if isinstance(v, dict) and v.get("status") in ("critical", "warning")}
        failures, new_failures, recovered = classify_transitions(previous, current)
        unconfigured = [k for k, v in current.items() if isinstance(v, dict) and v.get("status") == "not_configured"]
        current["not_configured"] = unconfigured
        current["overall"] = overall_status(current)
        current["failures"] = failures
        save_state(current)
        incident_token = os.getenv("MONITOR_INTERNAL_TOKEN", "")
        if incident_token:
            for key, details in new_failures.items():
                try:
                    request(os.getenv("MONITOR_APP_URL", "").rstrip("/") + "/api/platform/ops/internal/monitor-events",
                            method="POST", headers={"Content-Type": "application/json", "X-Monitor-Token": incident_token},
                            data=json.dumps({"check": key, "status": details.get("status"), "message": details.get("error") or str(details)}).encode())
                except Exception as exc:
                    print(f"INCIDENT CREATION FAILED for {key}: {type(exc).__name__}: {exc}", flush=True)
            for key in recovered:
                try:
                    request(os.getenv("MONITOR_APP_URL", "").rstrip("/") + "/api/platform/ops/internal/monitor-events",
                            method="POST", headers={"Content-Type": "application/json", "X-Monitor-Token": incident_token},
                            data=json.dumps({"check": key, "status": "ok", "message": "Monitoring check recovered"}).encode())
                except Exception as exc:
                    print(f"INCIDENT RECOVERY UPDATE FAILED for {key}: {type(exc).__name__}: {exc}", flush=True)
        if new_failures or recovered:
            lines = ["EduNexus platform monitoring update", "", "New alerts:"]
            lines += [f"- {k}: {v.get('error') or v}" for k, v in new_failures.items()] or ["- None"]
            lines += ["", "Recovered:"] + [f"- {k}" for k in recovered] if recovered else []
            try: send_email("EduNexus platform health alert", "\n".join(lines))
            except Exception as exc: print(f"ALERT DELIVERY FAILED: {type(exc).__name__}: {exc}", flush=True)
        test_recipient = os.getenv("MONITOR_SMTP_TEST_EMAIL")
        last_test = previous.get("last_smtp_test_epoch", 0)
        if test_recipient and current.get("smtp", {}).get("status") == "ok" and time.time() - last_test >= 86400:
            try:
                send_email("EduNexus SMTP delivery health check", "Automated SMTP delivery test succeeded.", test_recipient)
                current["last_smtp_test_epoch"] = time.time()
            except Exception as exc:
                current["smtp_delivery_test"] = {"status": "critical", "error": str(exc)}
                try: send_email("EduNexus SMTP delivery test failed", str(exc))
                except Exception: pass
        save_state(current)
        previous = current
        print(json.dumps(current, separators=(",", ":")), flush=True)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
