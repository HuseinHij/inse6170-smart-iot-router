from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, request, url_for
from .db import (
    add_whitelist_rule, delete_capture, delete_whitelist_rule,
    fetch_alerts, fetch_captures, fetch_data_rate_history, fetch_all_rate_history,
    fetch_devices, fetch_device_by_id,
    fetch_whitelist_rules, update_device_info
)
from .firewall import rebuild_whitelist


def create_app(conn, config, cap_manager):
    app = Flask(__name__, template_folder="../ui/templates", static_folder="../ui/static")
    app.secret_key = "iot-router-inse6170"
    title = config["ui"]["title"]
    interface = config["network"]["capture_interface"]
    history_days = config.get("retention", {}).get("history_days", 30)

    @app.route("/")
    def index():
        return render_template("index.html", title=title,
            device_count=len(fetch_devices(conn)),
            alert_count=len(fetch_alerts(conn)),
            capture_count=len(fetch_captures(conn)),
            rule_count=len(fetch_whitelist_rules(conn)),
)

    @app.route("/devices")
    def devices_page():
        return render_template("devices.html", title=title, devices=fetch_devices(conn))

    @app.route("/devices/<int:device_id>/edit", methods=["GET", "POST"])
    def edit_device(device_id):
        device = fetch_device_by_id(conn, device_id)
        if not device:
            return redirect(url_for("devices_page"))
        if request.method == "POST":
            update_device_info(conn, device_id,
                request.form.get("device_name") or None,
                request.form.get("model") or None,
                request.form.get("version") or None,
                request.form.get("description") or None,
                request.form.get("notes") or None)
            return redirect(url_for("devices_page"))
        return render_template("edit_device.html", title=title, device=device)

    @app.route("/alerts")
    def alerts_page():
        return render_template("alerts.html", title=title, alerts=fetch_alerts(conn))

    @app.route("/captures")
    def captures_page():
        return render_template("captures.html", title=title,
            captures=fetch_captures(conn),
            devices=fetch_devices(conn),
            active_ids=list(cap_manager.active.keys()))

    @app.route("/captures/start", methods=["POST"])
    def start_capture():
        mac = request.form.get("device_mac") or None
        filename = request.form.get("filename") or "capture"
        duration_raw = request.form.get("duration") or ""
        count_raw = request.form.get("packet_count") or ""
        duration = int(duration_raw) if duration_raw.isdigit() else None
        count = int(count_raw) if count_raw.isdigit() else None
        cap_manager.start_capture(interface, filename, mac, duration, count)
        return redirect(url_for("captures_page"))

    @app.route("/captures/<int:capture_id>/stop", methods=["POST"])
    def stop_capture(capture_id):
        cap_manager.stop_capture(capture_id)
        return redirect(url_for("captures_page"))

    @app.route("/captures/<int:capture_id>/delete", methods=["POST"])
    def delete_capture_route(capture_id):
        path = delete_capture(conn, capture_id)
        if path:
            Path(path).unlink(missing_ok=True)
        return redirect(url_for("captures_page"))

    @app.route("/captures/delete-all", methods=["POST"])
    def delete_all_captures():
        for c in fetch_captures(conn):
            Path(c["pcap_path"]).unlink(missing_ok=True)
        conn.execute("DELETE FROM captures")
        conn.commit()
        return redirect(url_for("captures_page"))

    @app.route("/rules")
    def rules_page():
        return render_template("rules.html", title=title,
            rules=fetch_whitelist_rules(conn), devices=fetch_devices(conn))

    @app.route("/rules/add", methods=["POST"])
    def add_rule():
        mac = request.form.get("device_mac") or None
        dest = request.form.get("allowed_dest") or None
        port_raw = request.form.get("allowed_port") or ""
        port = int(port_raw) if port_raw.isdigit() else None
        proto = request.form.get("protocol") or None
        desc = request.form.get("description") or None
        add_whitelist_rule(conn, mac, dest, port, proto, desc)
        rebuild_whitelist(conn)
        return redirect(url_for("rules_page"))

    @app.route("/rules/<int:rule_id>/delete", methods=["POST"])
    def delete_rule(rule_id):
        delete_whitelist_rule(conn, rule_id)
        rebuild_whitelist(conn)
        return redirect(url_for("rules_page"))


    @app.route("/history")
    def history_page():
        mac = request.args.get("mac", "")
        try:
            days = max(1, min(int(request.args.get("days", history_days)), 90))
        except ValueError:
            days = history_days
        history = fetch_data_rate_history(conn, mac, days) if mac else fetch_all_rate_history(conn, days)
        return render_template("history.html", title=title,
            history=history, devices=fetch_devices(conn), selected_mac=mac, days=days)

    @app.route("/api/devices")
    def api_devices():
        return jsonify([dict(r) for r in fetch_devices(conn)])

    @app.route("/api/alerts")
    def api_alerts():
        return jsonify([dict(r) for r in fetch_alerts(conn)])

    @app.route("/api/captures")
    def api_captures():
        return jsonify([dict(r) for r in fetch_captures(conn)])

    @app.route("/api/rules")
    def api_rules():
        return jsonify([dict(r) for r in fetch_whitelist_rules(conn)])

    @app.route("/api/history")
    def api_history():
        mac = request.args.get("mac", "")
        try:
            days = int(request.args.get("days", history_days))
        except ValueError:
            days = history_days
        rows = fetch_data_rate_history(conn, mac, days) if mac else fetch_all_rate_history(conn, days)
        return jsonify([dict(r) for r in rows])

    return app