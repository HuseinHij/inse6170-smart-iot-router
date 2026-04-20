from src.oui_lookup import OUILookup


def test_lookup_known_prefix(tmp_path):
    csv_path = tmp_path / "oui.csv"
    csv_path.write_text("prefix,vendor\nAA:BB:CC,Acme\n", encoding="utf-8")
    lookup = OUILookup(str(csv_path))
    assert lookup.lookup("AA:BB:CC:11:22:33") == "Acme"
