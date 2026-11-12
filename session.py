"""Application actions and information shown beside the board."""

import json
import os
from pathlib import Path

from computer import choose_move
from captured import missing_pieces
from game import (
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
        self.reset(opponent)

    def reset(self, opponent="human"):
        """Start a new game, discarding the previous one."""
        if opponent not in ("human", "computer"):
            raise ValueError("Unknown opponent")
        self.position = new_position()
        self.notation = []
        # Positions before each move, oldest first; undo restores the last one.
        self.history = []
        # The arguments given to play for each move, oldest first. A save keeps these;
        # loading replays them, which also rebuilds history for undo.
        self.played = []
        self.captured = []
        self.opponent = opponent

    def play(self, source, target, promotion=None):
        if self.game_over():
            raise ValueError("The game is over")
        before = copy_position(self.position)
        label = move(self.position, source, target, promotion)
        self.history.append(before)
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

    def undo(self):
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
        self.after_move()

    def to_save(self):
        return {
            "version": SAVE_VERSION,
            "opponent": self.opponent,
            "moves": self.played,
            "notation": self.notation,
            "board": self.position[0],
            "turn": self.position[1],
        }

    @classmethod
    def from_save(cls, data):
        """Rebuild a session by replaying the saved moves, checking them against the save."""
        if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
            raise ValueError("Not a saved game from this version")
        played = data.get("moves")
        if not isinstance(played, list) or not all(isinstance(m, list) for m in played):
            raise ValueError("The saved game has no valid move list")
        session = cls(data.get("opponent"))
        for entry in played:
            session.play(*entry)
        if (session.notation != data.get("notation")
                or session.position[0] != data.get("board")
                or session.position[1] != data.get("turn")):
            raise ValueError("The saved game does not match its moves")
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
        self.captured = missing_pieces(self.position)

    def view(self):
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

    def computer_to_move(self):
        return (self.opponent == "computer" and self.position[1] == "b"
                and not self.game_over())

    def sidebar(self):
        return {"captured": self.captured}

    def dispatch(self, action):
        command = action.get("action")
        if command == "move":
            if self.computer_to_move():
                raise ValueError("Wait for the computer's move")
            self.play(action.get("source"), action.get("target"), action.get("promotion"))
        elif command == "computer-move":
            if not self.computer_to_move():
                raise ValueError("It is not the computer's turn")
            self.play(*choose_move(self.position))
        elif command == "undo":
            self.undo()
        elif command == "save":
            self.save()
        elif command == "load":
            self.load()
        elif command == "legal":
            source = action.get("source")
            targets = legal_moves(self.position, source)
            if self.game_over():
                targets = []
            return {"targets": targets,
                    "promotions": [t for t in targets if promotes(self.position, source, t)]}
        elif command == "new":
            self.reset(action.get("opponent", "human"))
        elif command == "promotion-setup":
            self.reset()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        else:
            raise ValueError("Unknown action")
        return self.view()
