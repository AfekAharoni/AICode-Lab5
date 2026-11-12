"""Application actions and information shown beside the board."""

import json
import os
from pathlib import Path

from computer import choose_move
from game import (
    legal_moves,
    move,
    new_position,
    status,
    winner,
)


# Legal from the standard starting position under this game's rules.
# Next move: b7-a8, capturing a rook and reaching the last rank.
PROMOTION_SETUP = [
    ("a2", "a4"), ("h7", "h5"),
    ("a4", "a5"), ("h5", "h4"),
    ("a5", "a6"), ("h4", "h3"),
    ("a6", "b7"), ("h3", "g2"),
]

SAVE_VERSION = 1


class Session:
    # Where save and load read and write. Set per instance to use another file;
    # it is not reset when a new game starts.
    save_path = Path(__file__).parent / "game.save.json"

    def __init__(self, opponent="human"):
        if opponent not in ("human", "computer"):
            raise ValueError("Unknown opponent")
        self.position = new_position()
        self.notation = []
        self.opponent = opponent
        # Every move from the starting position, as the arguments given to play.
        # Replaying them rebuilds any earlier position.
        self.history = []

    def play(self, *args):
        label = move(self.position, *args)
        self.notation.append(label)
        self.history.append(list(args))
        self.after_move()

    def to_save(self):
        return {
            "version": SAVE_VERSION,
            "opponent": self.opponent,
            "history": self.history,
            "notation": self.notation,
            "board": self.position[0],
            "turn": self.position[1],
        }

    @classmethod
    def from_save(cls, data):
        """Rebuild a session by replaying the saved moves, checking them against the save."""
        if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
            raise ValueError("Not a saved game from this version")
        history = data.get("history")
        if not isinstance(history, list) or not all(isinstance(m, list) for m in history):
            raise ValueError("The saved game has no valid move history")
        session = cls(data.get("opponent"))
        for entry in history:
            session.play(*entry)
        if (session.notation != data.get("notation")
                or session.position[0] != data.get("board")
                or session.position[1] != data.get("turn")):
            raise ValueError("The saved game does not match its move history")
        return session

    def save(self):
        path = Path(self.save_path)
        temporary = path.with_name(path.name + ".tmp")
        try:
            temporary.write_text(json.dumps(self.to_save(), indent=1))
            os.replace(temporary, path)
        except OSError as error:
            raise ValueError(f"Could not save the game: {error.strerror}") from None

    def load(self):
        try:
            text = Path(self.save_path).read_text()
        except FileNotFoundError:
            raise ValueError("There is no saved game") from None
        except OSError as error:
            raise ValueError(f"Could not load the game: {error.strerror}") from None
        restored = self.from_save(json.loads(text))
        vars(self).update(vars(restored))

    def after_move(self):
        pass

    def view(self):
        return {
            "board": self.position[0],
            "turn": self.position[1],
            "moves": self.notation,
            "opponent": self.opponent,
            "status": status(self.position),
            "winner": winner(self.position),
            **self.sidebar(),
        }

    def computer_to_move(self):
        return (self.opponent == "computer" and self.position[1] == "b"
                and status(self.position) not in ("checkmate", "stalemate"))

    def sidebar(self):
        return {}

    def dispatch(self, action):
        command = action.get("action")
        if command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            self.play(action.get("source"), action.get("target"))
        elif command == "computer-move":
            if not self.computer_to_move():
                raise ValueError("It is not the computer's turn")
            self.play(*choose_move(self.position))
        elif command == "legal":
            return {"targets": legal_moves(self.position, action.get("source"))}
        elif command == "new":
            self.__init__(action.get("opponent", "human"))
        elif command == "promotion-setup":
            self.__init__()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        elif command == "save":
            self.save()
        elif command == "load":
            self.load()
        else:
            raise ValueError("Unknown action")
        return self.view()
