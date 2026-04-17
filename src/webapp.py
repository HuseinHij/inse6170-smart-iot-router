from __future__ import annotations

from flask import Flask, jsonify, render_template

from .db import fetch_alerts, fetch_captures, fetch_devices, fetch_whitelist_rules


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
        alerts = fetch_alerts(conn)[:5]
        captures = fetch_captures(conn)[:5]
        rules = fetch_whitelist_rules(conn)[:5]
        return render_template(
            "index.html",
            title=title,
            device_count=len(devices),
            alert_count=len(fetch_alerts(conn)),
            capture_count=len(fetch_captures(conn)),
            rule_count=len(fetch_whitelist_rules(conn)),
            alerts=alerts,
            captures=captures,
            devices=devices[:5],
            rules=rules,
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

    return app
