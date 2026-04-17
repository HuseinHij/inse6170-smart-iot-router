# Linux-Based Smart IoT Router

A proposal-aligned proof-of-concept Linux-based smart IoT router for small home or lab IoT environments.

## Project overview

This project turns a Linux machine into a smart IoT control point that can:

- act as a hotspot/router for IoT devices
- discover connected devices and maintain an inventory
- identify device vendors using MAC/OUI lookup
- capture network traffic into PCAP files
- enforce whitelist-based firewall rules
- detect suspicious or excessive behavior
- temporarily throttle traffic when needed
- store logs, alerts, and state in SQLite
- provide a local web dashboard for administration

## Main components

- **Linux networking layer** for hotspot and routing
- **Python backend** for orchestration and system logic
- **SQLite database** for devices, alerts, captures, and rules
- **Local web dashboard** for monitoring and administration
- **Packet capture module** using tcpdump/Scapy
- **Whitelist firewall module** using nftables
- **Monitoring and throttling module** using tc
- **MAC/OUI vendor lookup** for device identification

## Current project structure

```text
config/      project configuration files
data/        local OUI data and database storage
captures/    packet capture output
logs/        runtime logs
docs/        project documentation
src/         Python backend source code
ui/          dashboard templates and static assets