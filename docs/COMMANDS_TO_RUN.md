# Commands to run

## 1) Clone your repo and create a branch
```bash
git clone https://github.com/HuseinHij/inse6170-smart-iot-router.git
cd inse6170-smart-iot-router
git checkout -b proposal-build
```

## 2) Copy the package files into the repo
Unzip the provided project package and merge its contents into the repo root.

## 3) Create a Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4) Install Linux dependencies
Ubuntu/Debian example:
```bash
sudo apt update
sudo apt install -y hostapd nftables tcpdump sqlite3 python3-dev iw iproute2 net-tools
```

## 5) Check environment
```bash
bash scripts/check_env.sh
```

## 6) Edit runtime config
Update:
- `config/app.yaml`
- `config/hostapd.conf`

## 7) Start hotspot
```bash
bash scripts/setup_hotspot.sh wlan0 192.168.50.1/24 config/hostapd.conf
```

## 8) In another terminal, set NAT
```bash
bash scripts/setup_nat.sh eth0 wlan0 192.168.50.0/24
```

## 9) Start the app
```bash
source venv/bin/activate
python -m src.main
```

## 10) Open dashboard
Visit:
```text
http://127.0.0.1:8080
```
