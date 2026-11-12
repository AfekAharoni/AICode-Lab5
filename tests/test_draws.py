"""Automatic draw when neither side has enough material to checkmate."""

import pytest

from boards import assert_valid_board, board
from game import insufficient_material, new_position, status
from session import Session


DRAWN = {
    "kings only": board("wK e1", "bK e8"),
    "white bishop": board("wK e1", "bK e8", "wB c1"),
    "black bishop": board("wK e1", "bK e8", "bB c8"),
    "white knight": board("wK e1", "bK e8", "wN b1"),
    "black knight": board("wK e1", "bK e8", "bN g8"),
    "bishops on dark squares, both sides": board("wK e1", "bK e8", "wB c1", "bB f8"),
    "bishops on light squares, both sides": board("wK e1", "bK e8", "wB f1", "bB c8"),
    "two white bishops on one colour": board("wK e1", "bK e8", "wB c1", "wB e3"),
}

NOT_DRAWN = {
    "starting position": new_position()[0],
    "a pawn": board("wK e1", "bK e8", "wP a2"),
    "a black pawn": board("wK e1", "bK e8", "bP h7"),
    "a rook": board("wK e1", "bK e8", "wR a1"),
    "a queen": board("wK e1", "bK e8", "bQ d8"),
    "bishops on opposite colours": board("wK e1", "bK e8", "wB c1", "bB c8"),
    "bishop pair": board("wK e1", "bK e8", "wB c1", "wB f1"),
    "knight against bishop": board("wK e1", "bK e8", "wN b1", "bB c8"),
    "two knights": board("wK e1", "bK e8", "wN b1", "wN g1"),
    "knight against knight": board("wK e1", "bK e8", "wN b1", "bN g8"),
    "bishop and pawn": board("wK e1", "bK e8", "wB c1", "wP a2"),
}


@pytest.mark.parametrize("name", DRAWN)
def test_insufficient_material_is_detected(name):
    assert insufficient_material(DRAWN[name])


@pytest.mark.parametrize("name", NOT_DRAWN)
def test_enough_material_is_not_a_draw(name):
    assert not insufficient_material(NOT_DRAWN[name])


@pytest.mark.parametrize("side", "wb")
@pytest.mark.parametrize("name", DRAWN)
def test_session_reports_draw_for_either_side_to_move(name, side):
    session = Session()
    session.position = [DRAWN[name].copy(), side]
    view = session.view()
    assert view["draw"] == "insufficient material"
    assert view["winner"] is None
    assert session.game_over()


@pytest.mark.parametrize("name", NOT_DRAWN)
def test_session_has_no_draw_with_enough_material(name):
    session = Session()
    session.position = [NOT_DRAWN[name].copy(), "w"]
    assert session.view()["draw"] is None
    assert not session.game_over()


def test_capturing_the_last_rook_draws_and_ends_the_game():
    session = Session()
    session.position = [board("wK e1", "bK e8", "wN d4", "bR c6"), "w"]
    assert session.view()["draw"] is None
    view = session.dispatch({"action": "move", "source": "d4", "target": "c6"})
    assert view["moves"] == ["d4xc6"]
    assert view["draw"] == "insufficient material"
    assert view["status"] is None
    with pytest.raises(ValueError, match="over"):
        session.dispatch({"action": "move", "source": "e8", "target": "d8"})
    assert session.dispatch({"action": "legal", "source": "e8"}) == {"targets": []}


def test_computer_does_not_move_after_a_draw():
    session = Session("computer")
    session.position = [board("wK e1", "bK e8", "bN g8"), "b"]
    assert not session.computer_to_move()
    with pytest.raises(ValueError):
        session.dispatch({"action": "computer-move"})


def test_stalemate_is_still_reported_as_stalemate():
    session = Session()
    session.position = [board("bK a8", "wQ b6", "wK c1"), "b"]
    assert status(session.position) == "stalemate"
    assert session.view()["draw"] == "stalemate"


def test_checkmate_is_not_a_draw():
    session = Session()
    session.position = [board("wK g1", "wR a1", "bK g8", "bP f7", "bP g7", "bP h7"), "w"]
    view = session.dispatch({"action": "move", "source": "a1", "target": "a8"})
    assert view["status"] == "checkmate"
    assert view["draw"] is None
    assert view["winner"] == "White"


def test_new_game_clears_the_draw():
    session = Session()
    session.position = [DRAWN["kings only"].copy(), "w"]
    assert session.game_over()
    view = session.dispatch({"action": "new"})
    assert view["draw"] is None
    assert session.position == new_position()


@pytest.mark.parametrize("bad", [
    {"e1": "wK"},                                   # no black king
    {"e1": "wK", "e2": "bK"},                       # kings touching
    {"e1": "wK", "e8": "bK", "a1": "wP"},           # pawn on the first rank
    {"e1": "wK", "e8": "bK", "a2": "xQ"},           # unknown side
    {"e1": "wK", "e8": "bK", "a2": "wZ"},           # unknown piece
    {"e1": "wK", "e8": "bK", "i2": "wN"},           # off the board
])
def test_invalid_test_boards_are_rejected(bad):
    with pytest.raises((AssertionError, ValueError)):
        assert_valid_board(bad)
