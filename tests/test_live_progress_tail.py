from backend.app.services.live_progress_service import LiveProgressTail


def test_read_new_incremental(tmp_path):
    sink = tmp_path / "live.jsonl"
    tail = LiveProgressTail(sink)
    assert tail.read_new() == []  # fichier absent
    sink.write_text('{"generation": 1}\n', encoding="utf-8")
    assert tail.read_new() == [{"generation": 1}]
    assert tail.read_new() == []  # rien de nouveau
    with sink.open("a", encoding="utf-8") as f:
        f.write('{"generation": 2}\n')
    assert tail.read_new() == [{"generation": 2}]


def test_read_new_resets_on_truncation(tmp_path):
    sink = tmp_path / "live.jsonl"
    sink.write_text('{"generation": 1}\n{"generation": 2}\n', encoding="utf-8")
    tail = LiveProgressTail(sink)
    assert len(tail.read_new()) == 2
    sink.write_text('{"generation": 1}\n', encoding="utf-8")  # nouveau run, plus petit
    assert tail.read_new() == [{"generation": 1}]


def test_read_new_skips_invalid_and_partial(tmp_path):
    sink = tmp_path / "live.jsonl"
    sink.write_text('not json\n{"generation": 5}\n{partial', encoding="utf-8")
    tail = LiveProgressTail(sink)
    # 'not json' ignorée ; gen 5 ok ; '{partial' (pas de \n) pas encore consommée
    assert tail.read_new() == [{"generation": 5}]


def test_read_new_skips_valid_non_dict_scalars(tmp_path):
    sink = tmp_path / "live.jsonl"
    # lignes JSON valides mais non-objets : doivent être ignorées (contrat list[dict])
    sink.write_text('42\n"hello"\ntrue\n{"generation": 7}\n', encoding="utf-8")
    tail = LiveProgressTail(sink)
    assert tail.read_new() == [{"generation": 7}]
