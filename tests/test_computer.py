import random

import pytest

from computer import choose_move, evaluate
from game import Position, move, new_position, status
from session import Session


def test_takes_the_most_valuable_piece() -> None:
    position = [{"a1": "wK", "h8": "bK", "e5": "bR", "e2": "wQ", "b5": "wN"}, "b"]
    assert choose_move(position) == ("e5", "e2")


def test_prefers_checkmate_to_material() -> None:
    # b6xd4 wins a knight; Ra8-a1 is mate on the back rank.
    position = [
        {
            "g1": "wK",
            "f2": "wP",
            "g2": "wP",
            "h2": "wP",
            "d4": "wN",
            "g8": "bK",
            "a8": "bR",
            "b6": "bB",
        },
        "b",
    ]
    assert choose_move(position) == ("a8", "a1")


def test_scores_material_for_the_side() -> None:
    position = new_position()
    assert evaluate(position, "w") == 0
    del position[0]["d8"]
    assert evaluate(position, "w") == 9
    assert evaluate(position, "b") == -9


def test_no_move_when_the_game_is_over() -> None:
    position = [{"a8": "bK", "b6": "wQ", "c1": "wK"}, "b"]
    assert choose_move(position) is None


def test_ties_vary_with_the_random_source() -> None:
    moves = {choose_move(new_position(), random.Random(seed)) for seed in range(20)}
    assert len(moves) > 1


def test_new_game_against_the_computer() -> None:
    session = Session()
    view = session.dispatch({"action": "new", "opponent": "computer"})
    assert view["opponent"] == "computer"
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    with pytest.raises(ValueError, match="Wait for the computer"):
        session.dispatch({"action": "move", "source": "e7", "target": "e5"})
    view = session.dispatch({"action": "computer-move"})
    assert view["turn"] == "w"
    assert len(view["moves"]) == 2
    with pytest.raises(ValueError, match="not the computer's turn"):
        session.dispatch({"action": "computer-move"})


def test_two_player_game_has_no_computer() -> None:
    session = Session()
    assert session.view()["opponent"] == "human"
    session.dispatch({"action": "move", "source": "e2", "target": "e4"})
    with pytest.raises(ValueError, match="not the computer's turn"):
        session.dispatch({"action": "computer-move"})
    session.dispatch({"action": "move", "source": "e7", "target": "e5"})


def test_new_game_resets_the_opponent() -> None:
    session = Session()
    session.dispatch({"action": "new", "opponent": "computer"})
    session.dispatch({"action": "new"})
    assert session.view()["opponent"] == "human"
    with pytest.raises(ValueError, match="Unknown opponent"):
        session.dispatch({"action": "new", "opponent": "robot"})


# The computer's scoring of drawn positions (gaps found by the coverage review).

# Black to move, a queen up: Qg4-g3 stalemates White; every other move keeps the queen.
STALEMATE_TRAP: Position = [{"h1": "wK", "f2": "bK", "g4": "bQ"}, "b"]


def test_a_stalemate_scores_zero() -> None:
    trial = [STALEMATE_TRAP[0].copy(), "b"]
    move(trial, "g4", "g3")
    assert status(trial) == "stalemate"
    assert evaluate(trial, "b") == 0


@pytest.mark.parametrize("seed", range(10))
def test_computer_ahead_does_not_stalemate(seed: int) -> None:
    assert choose_move(STALEMATE_TRAP, random.Random(seed)) != ("g4", "g3")


# Black's two bishops on dark squares (6) against a knight (3). Taking the knight leaves
# only same-coloured bishops: a draw. Scoring it as +6 material made the computer take it.
TRADE_INTO_DRAW: Position = [{"a1": "wK", "h8": "bK", "c5": "bB", "e5": "bB", "d4": "wN"}, "b"]


def test_a_drawn_position_scores_zero_not_material() -> None:
    trial = [TRADE_INTO_DRAW[0].copy(), "b"]
    move(trial, "c5", "d4")
    assert evaluate(trial, "b") == 0


@pytest.mark.parametrize("seed", range(10))
def test_computer_ahead_does_not_trade_into_a_draw(seed: int) -> None:
    chosen = choose_move(TRADE_INTO_DRAW, random.Random(seed))
    assert chosen is not None
    assert chosen[1] != "d4"
