# Linux-Based Smart IoT Router

**INSE 6170 — Security of Systems and Networks**
Hussein Hijazi · Concordia University

A proof-of-concept Linux-based smart router designed for small-scale IoT environments (home or lab). The system turns a standard Linux machine into a monitored, secured network gateway with a local web admin dashboard.

---

## What it does

| Feature | Implementation |
|---|---|
| Wireless hotspot | `hostapd` daemon, WPA2-PSK |
| Internet routing / NAT | `nftables` masquerade + `ip_forward` |
| Device discovery & inventory | `ip neigh` ARP scan, stored in SQLite |
| MAC/OUI vendor identification | Local CSV lookup |
| Packet capture | `tcpdump` → rotating PCAP files |
| Whitelist firewall | `nftables` per-device rules, dynamically rebuilt from DB |
| Traffic anomaly detection | Scapy live sniff, per-MAC byte/packet thresholds |
| Traffic throttling (IPS response) | `tc tbf` qdisc, auto-released after timeout |
| Logging & alerting | SQLite — devices, alerts, rate events, system logs |
| Admin web dashboard | Flask + Jinja2, local network only |

---

## Project structure

```
config/
  app.yaml            Main configuration (interfaces, thresholds, paths)
  hostapd.conf        Wireless access point settings
  nftables.conf       Base firewall table skeleton

data/
  oui_sample.csv      MAC prefix → vendor lookup table
  router.db           SQLite database (auto-created on first run)

captures/             Rotating PCAP files written by tcpdump

src/
  main.py             Entry point — wires all modules together
  config.py           YAML config loader
  db.py               SQLite schema and all CRUD functions
  discovery.py        ARP-based device discovery (ip neigh)
  oui_lookup.py       MAC prefix → vendor name lookup
  capture.py          tcpdump subprocess manager
  monitor.py          Scapy traffic sampler + threshold evaluator
  firewall.py         nftables whitelist rule builder
  alerts.py           Alert creation helper
  scheduler.py        Background repeating task runner
  webapp.py           Flask routes (pages + JSON API)

ui/
  templates/          Jinja2 HTML templates (layout, dashboard, all pages)
  static/style.css    Dashboard stylesheet

scripts/
  setup_hotspot.sh    Configure AP interface and start hostapd
  setup_nat.sh        Enable ip_forward and nftables NAT masquerade
  apply_nftables.sh   Apply config/nftables.conf to running kernel
  reset_tc.sh         Remove tc traffic control rules from an interface
  check_env.sh        Verify all required tools are installed

tests/
  test_discovery.py   Unit test for ip neigh output parser
  test_oui_lookup.py  Unit test for OUI CSV lookup
```

---

## Requirements

- Linux machine with a wireless interface that supports AP mode (or a VM for demo)
- Python 3.10+
- Root/sudo access (required for hostapd, nftables, tcpdump, tc)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt` includes: `Flask`, `PyYAML`, `scapy`

Required system tools (check with `scripts/check_env.sh`):

```
hostapd  nft  tc  tcpdump  sqlite3  ip  sysctl
```

---

## Setup and running

### 1. Edit configuration

Open `config/app.yaml` and set the correct interface names for your machine:

```yaml
network:
  upstream_interface: eth0     # interface with internet access
  ap_interface: wlan0          # wireless interface for the hotspot
  capture_interface: wlan0
```

Update `config/hostapd.conf` with your desired SSID and passphrase.

### 2. Start the hotspot

```bash
sudo bash scripts/setup_hotspot.sh wlan0 192.168.50.1/24
```

### 3. Enable NAT routing

```bash
sudo bash scripts/setup_nat.sh eth0 wlan0 192.168.50.0/24
```

### 4. Run the application

```bash
sudo python3 -m src.main
```

The dashboard is available at: **http://192.168.50.1:8080**

---

## Dashboard pages

| URL | Description |
|---|---|
| `/` | Overview — stats, latest alerts, devices, captures |
| `/devices` | Full device inventory with vendor and timestamps |
| `/alerts` | All IPS alerts with severity |
| `/captures` | PCAP capture session log |
| `/rate-events` | Traffic throttle events (bytes/s, packets/s, action) |
| `/rules` | Whitelist firewall rules |
| `/logs` | System startup and runtime logs |

JSON API available at `/api/devices`, `/api/alerts`, `/api/captures`, `/api/rules`, `/api/rate-events`, `/api/logs`.

---

## How the IPS works

1. Every 20 seconds, `monitor.py` sniffs live traffic on the capture interface for 5 seconds using Scapy.
2. It calculates bytes/sec and packets/sec per source MAC address.
3. If a device exceeds `bytes_per_second_threshold` (500 000 B/s) or `packets_per_second_threshold` (1 000 pkt/s), it:
   - Creates a `high` severity alert in the database
   - Applies a `tc tbf` Token Bucket Filter at `1mbit` on the interface
   - Logs a rate event with exact measurements
   - Automatically removes the throttle after `throttle_duration_seconds` (120 s)

---

## How the whitelist firewall works

Whitelist rules are stored in the `whitelist_rules` table. On startup, `firewall.py` reads all enabled rules and dynamically builds an `nftables` ruleset:

- Creates table `inet iot_filter` with a forward chain set to `policy drop`
- Adds one `accept` rule per whitelist entry (per device MAC, destination IP, port, protocol)
- Pushes the full ruleset to the kernel via `nft -f -`

This means only explicitly whitelisted traffic is forwarded. Everything else is dropped.

---

## Running tests

```bash
python3 -m pytest tests/
```

---

## References

- Telecompetitor. *Report: People Underestimate Number of IoT Devices in Their Homes.* 2023.
- PMC. *A Systematic Review of IoT in Clinical Laboratories.* 2022.
- NYU Tandon. *Privacy and Security Threats in Smart Homes.* 2023.
- MDPI. *IoT Privacy and Security: Challenges and Solutions.* 2020.
- hostapd developer documentation — w1.fi
- tcpdump(1) man page — tcpdump.org
- nftables wiki — nftables.org
- tc(8) Linux manual page — man7.org
- IEEE OUI Registry — standards-oui.ieee.org