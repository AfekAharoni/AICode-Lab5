from pathlib import Path

import pytest

from session import Session


def test_display_after_capture_and_new_game() -> None:
    session = Session()
    assert session.view()["captured"] == []
    session.play("e2", "e4")
    session.play("d7", "d5")
    session.play("e4", "d5")
    assert session.view()["captured"] == ["bP"]
    session.dispatch({"action": "new"})
    assert session.view()["captured"] == []


# Interactions with undo and save/load (added when merging captured-pieces into main).


def play(session: Session, *moves: tuple[str, str]) -> None:
    for source, target in moves:
        session.dispatch({"action": "move", "source": source, "target": target})


def test_undoing_a_capture_removes_it_from_the_display() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    assert session.view()["captured"] == ["bP"]
    view = session.dispatch({"action": "undo"})
    assert view["captured"] == []
    assert session.position[0]["d5"] == "bP"


def test_both_sides_captures_are_shown_and_undone_one_at_a_time() -> None:
    session = Session()
    play(session, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"), ("d8", "d5"))
    assert sorted(session.view()["captured"]) == ["bP", "wP"]
    assert session.dispatch({"action": "undo"})["captured"] == ["bP"]
    assert session.dispatch({"action": "undo"})["captured"] == []


def test_undo_against_computer_removes_both_captures_of_the_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


def test_captured_pieces_survive_save_and_load(tmp_path: Path) -> None:
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


# Interactions with promotion (added when merging promotion into main).
# The display lists pieces actually captured, with their type at capture.
# Promotion alone is not a capture.


def promoted_on_a8() -> Session:
    """promotion-setup captures bP (a6xb7) and wP (h3xg2); b7xa8=Q captures bR."""
    session = Session()
    session.dispatch({"action": "promotion-setup"})
    session.dispatch({"action": "move", "source": "b7", "target": "a8", "promotion": "Q"})
    return session


def test_promotion_alone_is_not_a_capture() -> None:
    session = Session()
    session.position = [{"a1": "wK", "h6": "bK", "d7": "wP"}, "w"]
    view = session.dispatch({"action": "move", "source": "d7", "target": "d8", "promotion": "Q"})
    assert view["board"]["d8"] == "wQ"
    assert view["captured"] == []


def test_promoting_pawn_is_not_shown_as_captured() -> None:
    assert promoted_on_a8().view()["captured"] == ["bP", "bR", "wP"]


def test_captured_promoted_piece_is_shown_with_its_type_at_capture() -> None:
    session = promoted_on_a8()
    play(session, ("a7", "a5"), ("a8", "a6"), ("b8", "a6"))
    assert session.view()["moves"][-1] == "b8xa6"
    assert session.view()["captured"] == ["bP", "bR", "wP", "wQ"]


def test_undoing_a_capturing_promotion_restores_pawn_and_display() -> None:
    session = promoted_on_a8()
    view = session.dispatch({"action": "undo"})
    assert view["board"]["b7"] == "wP"
    assert view["board"]["a8"] == "bR"
    assert view["captured"] == ["bP", "wP"]


def test_promotion_and_captures_survive_save_and_load(tmp_path: Path) -> None:
    original = promoted_on_a8()
    original.save_path = tmp_path / "game.save.json"
    original.dispatch({"action": "save"})
    fresh = Session()
    fresh.save_path = original.save_path
    view = fresh.dispatch({"action": "load"})
    assert view["board"]["a8"] == "wQ"
    assert view["moves"][-1].startswith("b7xa8=Q")
    assert view["captured"] == ["bP", "bR", "wP"]
    assert fresh.dispatch({"action": "undo"})["board"]["b7"] == "wP"
