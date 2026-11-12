from session import Session


def test_display_after_capture_and_new_game():
    session = Session()
    assert session.view()["captured"] == []
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")
    assert session.view()["captured"] == ["bP"]
    session.dispatch({"action": "new"})
    assert session.view()["captured"] == []


# Interactions with undo and save/load (added when merging captured-pieces into main).

def play(session, *moves):
    for source, target in moves:
        session.dispatch({"action": "move", "source": source, "target": target})


def test_undoing_a_capture_removes_it_from_the_display():
    session = Session()
    play(session, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    assert session.view()["captured"] == ["bP"]
    view = session.dispatch({"action": "undo"})
    assert view["captured"] == []
    assert session.position[0]["d5"] == "bP"


def test_both_sides_captures_are_shown_and_undone_one_at_a_time():
    session = Session()
    play(session, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"), ("d8", "d5"))
    assert sorted(session.view()["captured"]) == ["bP", "wP"]
    assert session.dispatch({"action": "undo"})["captured"] == ["bP"]
    assert session.dispatch({"action": "undo"})["captured"] == []


def test_undo_against_computer_removes_both_captures_of_the_turn(monkeypatch):
    replies = iter([("d7", "d5"), ("d8", "d5")])
    monkeypatch.setattr("session.choose_move", lambda position: next(replies))
    session = Session("computer")
    play(session, ("e2", "e4"))
    session.dispatch({"action": "computer-move"})
    play(session, ("e4", "d5"))
    view = session.dispatch({"action": "computer-move"})
    assert sorted(view["captured"]) == ["bP", "wP"]
    view = session.dispatch({"action": "undo"})
    assert view["captured"] == []
    assert view["moves"] == ["e2-e4", "d7-d5"]


def test_captured_pieces_survive_save_and_load(tmp_path):
    original = Session()
    original.save_path = tmp_path / "game.save.json"
    play(original, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    original.dispatch({"action": "save"})
    original.dispatch({"action": "new"})
    assert original.view()["captured"] == []

    fresh = Session()
    fresh.save_path = original.save_path
    assert fresh.dispatch({"action": "load"})["captured"] == ["bP"]
    # Undo after loading still removes the capture made before saving.
    assert fresh.dispatch({"action": "undo"})["captured"] == []
