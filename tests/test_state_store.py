from anka.storage.state import JsonStateStore


def test_state_store_persists_atomically(tmp_path):
    path = tmp_path / "hafiza.json"
    store = JsonStateStore(path)

    store.save({"notlar": ["not"], "gorevler": ["görev"]})

    assert JsonStateStore(path).load() == {"notlar": ["not"], "gorevler": ["görev"]}
    assert not path.with_suffix(".json.tmp").exists()


def test_state_store_returns_default_for_corrupt_file(tmp_path):
    path = tmp_path / "hafiza.json"
    path.write_text("{bozuk", encoding="utf-8")

    assert JsonStateStore(path).load({"notlar": []}) == {"notlar": []}
