from __future__ import annotations

from flask import Flask, jsonify, render_template

from .db import (
    fetch_alerts,
    fetch_captures,
    fetch_devices,
    fetch_whitelist_rules,
    fetch_rate_events,
    fetch_system_logs,
)


def create_app(conn, config: dict) -> Flask:
    app = Flask(
        __name__,
        template_folder="../ui/templates",
        static_folder="../ui/static",
    )

    title = config["ui"]["title"]

    @app.route("/")
    def index():
        devices = fetch_devices(conn)
        alerts = fetch_alerts(conn)
        captures = fetch_captures(conn)
        rules = fetch_whitelist_rules(conn)
        rate_events = fetch_rate_events(conn)
        return render_template(
            "index.html",
            title=title,
            device_count=len(devices),
            alert_count=len(alerts),
            capture_count=len(captures),
            rule_count=len(rules),
            rate_event_count=len(rate_events),
            alerts=alerts[:5],
            captures=captures[:5],
            devices=devices[:5],
            rules=rules[:5],
            rate_events=rate_events[:5],
        )

    @app.route("/devices")
    def devices_page():
        return render_template("devices.html", title=title, devices=fetch_devices(conn))

    @app.route("/alerts")
    def alerts_page():
        return render_template("alerts.html", title=title, alerts=fetch_alerts(conn))

    @app.route("/captures")
    def captures_page():
        return render_template("captures.html", title=title, captures=fetch_captures(conn))

    @app.route("/rules")
    def rules_page():
        return render_template("rules.html", title=title, rules=fetch_whitelist_rules(conn))

    @app.route("/rate-events")
    def rate_events_page():
        return render_template("rate_events.html", title=title, rate_events=fetch_rate_events(conn))

    @app.route("/logs")
    def logs_page():
        return render_template("logs.html", title=title, logs=fetch_system_logs(conn))

    # JSON API endpoints
    @app.route("/api/devices")
    def devices_api():
        return jsonify([dict(row) for row in fetch_devices(conn)])

    @app.route("/api/alerts")
    def alerts_api():
        return jsonify([dict(row) for row in fetch_alerts(conn)])

    @app.route("/api/captures")
    def captures_api():
        return jsonify([dict(row) for row in fetch_captures(conn)])

    @app.route("/api/rules")
    def rules_api():
        return jsonify([dict(row) for row in fetch_whitelist_rules(conn)])

    @app.route("/api/rate-events")
    def rate_events_api():
        return jsonify([dict(row) for row in fetch_rate_events(conn)])

    @app.route("/api/logs")
    def logs_api():
        return jsonify([dict(row) for row in fetch_system_logs(conn)])

    return app