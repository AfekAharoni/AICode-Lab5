import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from game import new_position
from server import make_server
from session import Session


def session_saving_to(path: Path, opponent: str = "human") -> Session:
    session = Session(opponent)
    session.save_path = path
    return session


def play(session: Session, *moves: tuple[str, str]) -> None:
    for source, target in moves:
        session.dispatch({"action": "move", "source": source, "target": target})


def test_save_and_load_in_a_fresh_session(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    original = session_saving_to(path)
    play(original, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    original.dispatch({"action": "save"})

    fresh = session_saving_to(path)
    view = fresh.dispatch({"action": "load"})
    assert view == original.view()
    assert view["moves"] == ["e2-e4", "d7-d5", "e4xd5"]
    assert view["turn"] == "b"
    assert fresh.position == original.position
    # The game continues from where it was saved.
    play(fresh, ("d8", "d5"))
    assert fresh.position[0]["d5"] == "bQ"


def test_history_is_preserved_and_rebuilds_earlier_positions(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    original = session_saving_to(path)
    play(original, ("e2", "e4"), ("e7", "e5"), ("g1", "f3"))
    original.dispatch({"action": "save"})

    fresh = session_saving_to(path)
    fresh.dispatch({"action": "load"})
    assert fresh.played == [["e2", "e4"], ["e7", "e5"], ["g1", "f3"]]
    assert fresh.history == original.history


def test_opponent_mode_is_restored(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    original = session_saving_to(path, "computer")
    play(original, ("e2", "e4"))
    original.dispatch({"action": "save"})

    fresh = session_saving_to(path)
    view = fresh.dispatch({"action": "load"})
    assert view["opponent"] == "computer"
    # Saved with the computer to move: it is still the computer's turn.
    assert fresh.computer_to_move()
    with pytest.raises(ValueError, match="Wait for the computer"):
        play(fresh, ("e7", "e5"))
    view = fresh.dispatch({"action": "computer-move"})
    assert view["turn"] == "w"
    assert len(view["moves"]) == 2


def test_computer_moves_are_saved(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    original = session_saving_to(path, "computer")
    play(original, ("e2", "e4"))
    original.dispatch({"action": "computer-move"})
    original.dispatch({"action": "save"})

    fresh = session_saving_to(path)
    fresh.dispatch({"action": "load"})
    assert fresh.view() == original.view()
    assert len(fresh.played) == 2


def test_new_game_keeps_the_save_file_and_can_load_again(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    session = session_saving_to(path)
    play(session, ("e2", "e4"))
    session.dispatch({"action": "save"})
    session.dispatch({"action": "new", "opponent": "computer"})
    assert session.save_path == path
    view = session.dispatch({"action": "load"})
    assert view["moves"] == ["e2-e4"]
    assert view["opponent"] == "human"


def test_saving_again_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    session = session_saving_to(path)
    session.dispatch({"action": "save"})
    play(session, ("e2", "e4"))
    session.dispatch({"action": "save"})
    fresh = session_saving_to(path)
    assert fresh.dispatch({"action": "load"})["moves"] == ["e2-e4"]
    assert list(tmp_path.iterdir()) == [path]


def test_saved_finished_game_loads_as_finished(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    session = session_saving_to(path)
    # Fool's mate.
    play(session, ("f2", "f3"), ("e7", "e5"), ("g2", "g4"), ("d8", "h4"))
    assert session.view()["status"] == "checkmate"
    session.dispatch({"action": "save"})
    view = session_saving_to(path).dispatch({"action": "load"})
    assert view["status"] == "checkmate"
    assert view["winner"] == "Black"


def test_load_without_a_save_fails_and_keeps_the_game(tmp_path: Path) -> None:
    session = session_saving_to(tmp_path / "missing.save.json")
    play(session, ("e2", "e4"))
    before = session.view()
    with pytest.raises(ValueError, match="no saved game"):
        session.dispatch({"action": "load"})
    assert session.view() == before


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(version=99),
        lambda data: data.update(opponent="robot"),
        lambda data: data.update(moves="e2e4"),
        lambda data: data["moves"].append(["e2", "e5"]),  # illegal move
        lambda data: data["moves"].append(["e2"]),  # incomplete move
        lambda data: data["board"].pop("a1"),  # board disagrees with the moves
        lambda data: data.update(turn="w"),
        lambda data: data["notation"].append("a2-a3"),
    ],
)
def test_corrupt_save_is_rejected_and_keeps_the_game(
    tmp_path: Path, change: Callable[[dict[str, Any]], object]
) -> None:
    path = tmp_path / "game.save.json"
    saver = session_saving_to(path)
    play(saver, ("e2", "e4"))
    saver.dispatch({"action": "save"})
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))

    session = session_saving_to(path)
    play(session, ("d2", "d4"))
    before = session.view()
    with pytest.raises(ValueError, match="saved game|Unknown opponent|not allowed"):
        session.dispatch({"action": "load"})
    assert session.view() == before


def test_unreadable_save_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    path.write_text("not json {")
    session = session_saving_to(path)
    with pytest.raises(ValueError, match="damaged"):
        session.dispatch({"action": "load"})
    assert session.position == new_position()


def test_save_to_a_missing_directory_reports_an_error(tmp_path: Path) -> None:
    session = session_saving_to(tmp_path / "no" / "such" / "dir" / "game.save.json")
    with pytest.raises(ValueError, match="Could not save"):
        session.dispatch({"action": "save"})


def test_save_and_load_through_the_server_and_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"

    def run(*actions: dict[str, Any]) -> list[tuple[int, Any]]:
        server = make_server(0, save_path=path)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            results = []
            for action in actions:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/api/action",
                    data=json.dumps(action).encode(),
                    headers={"Content-Type": "application/json"},
                )
                try:
                    with urllib.request.urlopen(request) as response:
                        results.append((response.status, json.load(response)))
                except urllib.error.HTTPError as error:
                    results.append((error.code, json.load(error)))
            return results
        finally:
            server.shutdown()
            server.server_close()

    ((status, _),) = run({"action": "load"})
    assert status == 400
    run(
        {"action": "new", "opponent": "computer"},
        {"action": "move", "source": "e2", "target": "e4"},
        {"action": "save"},
    )
    ((status, view),) = run({"action": "load"})
    assert status == 200
    assert view["moves"] == ["e2-e4"]
    assert view["opponent"] == "computer"
    assert view["turn"] == "b"


def test_undo_after_load_takes_back_moves_made_before_saving(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    original = session_saving_to(path)
    play(original, ("e2", "e4"), ("d7", "d5"), ("e4", "d5"))
    original.dispatch({"action": "save"})

    fresh = session_saving_to(path)
    fresh.dispatch({"action": "load"})
    view = fresh.dispatch({"action": "undo"})
    assert view["moves"] == ["e2-e4", "d7-d5"]
    assert fresh.position[0]["d5"] == "bP"
    assert view["turn"] == "w"
    for _ in range(2):
        fresh.dispatch({"action": "undo"})
    assert fresh.position == new_position()
    assert fresh.played == []


def test_undo_against_the_computer_after_load_takes_back_a_full_turn(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    original = session_saving_to(path, "computer")
    play(original, ("e2", "e4"))
    original.dispatch({"action": "computer-move"})
    original.dispatch({"action": "save"})

    fresh = session_saving_to(path)
    view = fresh.dispatch({"action": "load"})
    assert view["opponent"] == "computer"
    view = fresh.dispatch({"action": "undo"})
    assert view["moves"] == []
    assert fresh.position == new_position()


def test_save_after_undo_keeps_only_the_remaining_moves(tmp_path: Path) -> None:
    path = tmp_path / "game.save.json"
    session = session_saving_to(path)
    play(session, ("e2", "e4"), ("e7", "e5"))
    session.dispatch({"action": "undo"})
    session.dispatch({"action": "save"})
    fresh = session_saving_to(path)
    assert fresh.dispatch({"action": "load"})["moves"] == ["e2-e4"]
    assert fresh.played == [["e2", "e4"]]


def test_a_save_path_that_cannot_be_read_gives_a_clear_error(tmp_path: Path) -> None:
    session = session_saving_to(tmp_path)  # a directory, not a file
    with pytest.raises(ValueError, match="Could not load the game"):
        session.dispatch({"action": "load"})
    assert session.position == new_position()


@pytest.mark.parametrize("entry", [["e2"], ["e2", "e4", "Q", "x"], ["e2", 4], "e2e4"])
def test_malformed_saved_move_is_rejected_as_a_value_error(tmp_path: Path, entry: object) -> None:
    path = tmp_path / "game.save.json"
    data = {
        "version": 1,
        "opponent": "human",
        "moves": [entry],
        "notation": [],
        "board": {},
        "turn": "w",
    }
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="no valid move list"):
        session_saving_to(path).dispatch({"action": "load"})
