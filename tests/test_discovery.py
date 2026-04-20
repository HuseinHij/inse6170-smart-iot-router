from src.discovery import parse_ip_neigh


def test_parse_ip_neigh():
    sample = "192.168.50.10 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE\n"
    devices = parse_ip_neigh(sample)
    assert devices[0]["ip_address"] == "192.168.50.10"
    assert devices[0]["mac_address"] == "aa:bb:cc:dd:ee:ff"
