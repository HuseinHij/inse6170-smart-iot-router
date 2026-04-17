# Linux-Based Smart IoT Router

A proposal-aligned proof-of-concept Linux hotspot/router for small IoT environments.

## What this project does

This project turns a Linux machine into a smart IoT control point that can:

- run as a wireless hotspot/router
- discover connected devices and keep an inventory
- identify vendors by MAC/OUI lookup
- capture traffic into PCAP files
- enforce whitelist-based firewall rules
- detect suspicious or excessive traffic
- temporarily throttle devices with `tc`
- store logs, alerts, and state in SQLite
- expose a local web dashboard for administration

## Folder structure

```text
config/      runtime configuration, hostapd, nftables
data/        SQLite database and local OUI data
captures/    generated PCAP files
logs/        application logs
docs/        setup notes and design docs
scripts/     Linux helper scripts
src/         Python backend
ui/          templates and static files
tests/       small unit tests
```

## Quick start

1. Create a virtual environment and install Python dependencies.
2. Configure `config/app.yaml`.
3. Run `scripts/check_env.sh`.
4. Configure Linux hotspot/NAT with the scripts in `scripts/`.
5. Start the app with:

```bash
python -m src.main
```

6. Open the dashboard at `http://<router-ip>:8080`.

## Important notes

- Run on a Linux machine.
- Packet capture, firewall changes, AP mode, and traffic shaping require elevated privileges.
- Use a dedicated test machine or VM host with compatible Wi-Fi hardware.
- Prefer two interfaces:
  - upstream internet interface, for example `eth0`
  - AP interface, for example `wlan0`

## Suggested commit plan

See `docs/IMPLEMENTATION_GUIDE.md`.
