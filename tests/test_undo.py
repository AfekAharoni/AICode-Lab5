"""Undo: restores board, side to move, captures and notation.

Decision: against the computer, undo takes back a full turn (the computer's reply and
the player's move), so it is the player's move again.
"""

import random

from game import new_position
from session import Session


def play(session, *moves):
    for source, target in moves:
        session.dispatch({"action": "move", "source": source, "target": target})


def undo(session):
    return session.dispatch({"action": "undo"})


def test_undo_at_the_beginning_does_nothing():
    session = Session()
    view = undo(session)
    assert session.position == new_position()
    assert view["moves"] == []
    assert view["turn"] == "w"


def test_undo_one_move_restores_board_and_turn():
    session = Session()
    play(session, ("e2", "e4"))
    view = undo(session)
    assert session.position == new_position()
    assert view["turn"] == "w"
    assert view["moves"] == []


def test_undo_restores_captured_piece_and_side_to_move():
    session = Session()
    play(session, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    assert session.position[0]["d5"] == "wP"
    view = undo(session)
    assert session.position[0]["d5"] == "bP"
    assert session.position[0]["e4"] == "wP"
    assert len(session.position[0]) == 32
    assert view["turn"] == "w"
    assert view["moves"] == ["e2-e4", "d7-d5"]


def test_repeated_undo_returns_to_start_then_stops():
    session = Session()
    play(session, ("e2", "e4"), ("e7", "e5"), ("g1", "f3"))
    for _ in range(5):
        undo(session)
    assert session.position == new_position()
    assert session.notation == []


def test_undo_does_not_share_board_with_history():
    """Moves after an undo must not corrupt earlier saved positions."""
    session = Session()
    play(session, ("e2", "e4"), ("e7", "e5"))
    undo(session)
    play(session, ("d7", "d5"), ("e4", "d5"))
    undo(session)
    undo(session)
    undo(session)
    assert session.position == new_position()


def test_play_continues_normally_after_undo():
    session = Session()
    play(session, ("e2", "e4"))
    undo(session)
    play(session, ("d2", "d4"), ("d7", "d5"))
    assert session.notation == ["d2-d4", "d7-d5"]
    assert session.position[0]["d4"] == "wP"
    assert "e4" not in session.position[0]


def test_undo_after_checkmate_resumes_the_game():
    session = Session()
    play(session, ("f2", "f3"), ("e7", "e5"), ("g2", "g4"), ("d8", "h4"))
    assert session.view()["status"] == "checkmate"
    view = undo(session)
    assert view["status"] is None
    assert view["turn"] == "b"
    assert "h4" in session.dispatch({"action": "legal", "source": "d8"})["targets"]


def test_new_game_clears_undo_history():
    session = Session()
    play(session, ("e2", "e4"))
    session.dispatch({"action": "new"})
    undo(session)
    assert session.position == new_position()
    assert session.notation == []


def test_undo_against_computer_takes_back_both_moves():
    random.seed(0)
    session = Session("computer")
    play(session, ("e2", "e4"))
    session.dispatch({"action": "computer-move"})
    assert len(session.notation) == 2
    view = undo(session)
    assert session.position == new_position()
    assert view["turn"] == "w"
    assert view["moves"] == []
    assert view["opponent"] == "computer"


def test_undo_against_computer_keeps_earlier_turns():
    random.seed(1)
    session = Session("computer")
    play(session, ("e2", "e4"))
    session.dispatch({"action": "computer-move"})
    after_first_turn = [session.position[0].copy(), session.position[1]]
    first_turn = list(session.notation)
    play(session, ("d2", "d4"))
    session.dispatch({"action": "computer-move"})
    undo(session)
    assert session.position == after_first_turn
    assert session.notation == first_turn
    assert not session.computer_to_move()


def test_undo_against_computer_before_it_replies_takes_back_one_move():
    session = Session("computer")
    play(session, ("e2", "e4"))
    assert session.computer_to_move()
    undo(session)
    assert session.position == new_position()
    assert session.notation == []


def test_undo_after_player_checkmates_computer_takes_back_one_move():
    session = Session("computer")
    session.position = [{"g1": "wK", "a1": "wR", "g8": "bK",
                         "f7": "bP", "g7": "bP", "h7": "bP"}, "w"]
    start = [session.position[0].copy(), "w"]
    play(session, ("a1", "a8"))
    assert session.view()["status"] == "checkmate"
    undo(session)
    assert session.position == start
    assert session.view()["status"] is None
