"""Application actions and information shown beside the board."""

import json
import os
from pathlib import Path
from typing import Any

from captured import captured_pieces
from computer import choose_move
from game import (
    Position,
    copy_position,
    insufficient_material,
    legal_moves,
    move,
    new_position,
    promotes,
    status,
    winner,
)

# Legal from the standard starting position under this game's rules.
# Next move: b7-a8, capturing a rook and reaching the last rank.
PROMOTION_SETUP = [
    ("a2", "a4"),
    ("h7", "h5"),
    ("a4", "a5"),
    ("h5", "h4"),
    ("a5", "a6"),
    ("h4", "h3"),
    ("a6", "b7"),
    ("h3", "g2"),
]

SAVE_VERSION = 1
# A saved move is [source, target] or [source, target, promotion piece].
SAVED_MOVE_LENGTHS = (2, 3)


def valid_move_entry(entry: object) -> bool:
    return (
        isinstance(entry, list)
        and len(entry) in SAVED_MOVE_LENGTHS
        and all(isinstance(item, str) for item in entry)
    )


class Session:
    # Where save and load read and write. Set per instance to use another file;
    # it is not reset when a new game starts.
    save_path = Path(__file__).parent / "game.save.json"

    def __init__(self, opponent: str = "human") -> None:
        self.reset(opponent)

    def reset(self, opponent: str = "human") -> None:
        """Start a new game, discarding the previous one."""
        if opponent not in ("human", "computer"):
            raise ValueError("Unknown opponent")
        self.position = new_position()
        self.notation: list[str] = []
        # Positions before each move, oldest first; undo restores the last one.
        self.history: list[Position] = []
        # The arguments given to play for each move, oldest first. A save keeps these;
        # loading replays them, which also rebuilds history for undo.
        self.played: list[list[str]] = []
        # The piece each move took (None if it took nothing), parallel to history.
        self.captures: list[str | None] = []
        self.captured: list[str] = []
        self.opponent = opponent

    def play(self, source: str, target: str, promotion: str | None = None) -> None:
        if self.game_over():
            raise ValueError("The game is over")
        before = copy_position(self.position)
        taken = self.position[0].get(target)
        label = move(self.position, source, target, promotion)
        self.history.append(before)
        self.captures.append(taken)
        self.played.append([source, target] + ([promotion] if promotion else []))
        self.notation.append(label)
        self.after_move()

    def draw(self) -> str | None:
        """Why the game is drawn, or None."""
        if status(self.position) == "stalemate":
            return "stalemate"
        if insufficient_material(self.position[0]):
            return "insufficient material"
        return None

    def game_over(self) -> bool:
        return status(self.position) == "checkmate" or self.draw() is not None

    def undo(self) -> None:
        """Take back the last move; against the computer, take back a full turn.

        Against the computer, undo removes the computer's reply and the player's move
        before it, so it is White's (the player's) turn again. If the computer has not
        replied (for example, the player just gave checkmate), only the player's move
        is undone. Undo at the beginning does nothing.
        """
        if not self.history:
            return
        count = 1
        if self.opponent == "computer" and self.position[1] == "w":
            count = 2
        for _ in range(min(count, len(self.history))):
            self.position = self.history.pop()
            self.notation.pop()
            self.played.pop()
            self.captures.pop()
        self.after_move()

    def to_save(self) -> dict[str, Any]:
        return {
            "version": SAVE_VERSION,
            "opponent": self.opponent,
            "moves": self.played,
            "notation": self.notation,
            "board": self.position[0],
            "turn": self.position[1],
        }

    @classmethod
    def from_save(cls, data: object) -> "Session":
        """Rebuild a session by replaying the saved moves, checking them against the save."""
        if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
            raise ValueError("Not a saved game from this version")
        played = data.get("moves")
        if not isinstance(played, list) or not all(valid_move_entry(m) for m in played):
            raise ValueError("The saved game has no valid move list")
        session = cls(data.get("opponent", ""))  # rejects an unknown opponent
        for entry in played:
            session.play(*entry)
        if (
            session.notation != data.get("notation")
            or session.position[0] != data.get("board")
            or session.position[1] != data.get("turn")
        ):
            raise ValueError("The saved game does not match its moves")
        return session

    def save(self) -> None:
        path = Path(self.save_path)
        temporary = path.with_name(path.name + ".tmp")
        try:
            temporary.write_text(json.dumps(self.to_save(), indent=1))
            os.replace(temporary, path)
        except OSError as error:
            raise ValueError(f"Could not save the game: {error.strerror}") from None

    def load(self) -> None:
        try:
            text = Path(self.save_path).read_text()
        except FileNotFoundError:
            raise ValueError("There is no saved game") from None
        except OSError as error:
            raise ValueError(f"Could not load the game: {error.strerror}") from None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError("The saved game is damaged") from None
        restored = self.from_save(data)
        vars(self).update(vars(restored))

    def after_move(self) -> None:
        self.captured = captured_pieces(self.captures)

    def view(self) -> dict[str, Any]:
        return {
            "board": self.position[0],
            "turn": self.position[1],
            "moves": self.notation,
            "opponent": self.opponent,
            "status": status(self.position),
            "winner": winner(self.position),
            "draw": self.draw(),
            **self.sidebar(),
        }

    def computer_to_move(self) -> bool:
        return self.opponent == "computer" and self.position[1] == "b" and not self.game_over()

    def sidebar(self) -> dict[str, Any]:
        return {"captured": self.captured}

    def legal(self, source: object) -> dict[str, list[str]]:
        """Where the piece on source may go, and which of those squares promote."""
        targets = legal_moves(self.position, source)
        if self.game_over():
            return {"targets": [], "promotions": []}
        assert isinstance(source, str)  # legal_moves() rejects anything else
        return {
            "targets": targets,
            "promotions": [t for t in targets if promotes(self.position, source, t)],
        }

    def computer_move(self) -> None:
        if not self.computer_to_move():
            raise ValueError("It is not the computer's turn")
        chosen = choose_move(self.position)
        if chosen is None:
            raise ValueError("The computer has no move")
        self.play(*chosen)

    def dispatch(self, action: dict[str, Any]) -> dict[str, Any]:
        command = action.get("action")
        simple = {
            "computer-move": self.computer_move,
            "undo": self.undo,
            "save": self.save,
            "load": self.load,
        }
        if command in simple:
            simple[command]()
        elif command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            source, target = action.get("source"), action.get("target")
            if not isinstance(source, str) or not isinstance(target, str):
                raise ValueError("Expected a source and a target square")
            self.play(source, target, action.get("promotion"))
        elif command == "legal":
            return self.legal(action.get("source"))
        elif command == "new":
            self.reset(action.get("opponent", "human"))
        elif command == "promotion-setup":
            self.reset()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        else:
            raise ValueError("Unknown action")
        return self.view()
