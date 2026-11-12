"""Application actions and information shown beside the board."""

from computer import choose_move
from game import (
    copy_position,
    insufficient_material,
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


class Session:
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
        self.opponent = opponent

    def play(self, source, target):
        if self.game_over():
            raise ValueError("The game is over")
        before = copy_position(self.position)
        label = move(self.position, source, target)
        self.history.append(before)
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
        self.after_move()

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
            "draw": self.draw(),
            **self.sidebar(),
        }

    def computer_to_move(self):
        return (self.opponent == "computer" and self.position[1] == "b"
                and not self.game_over())

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
        elif command == "undo":
            self.undo()
        elif command == "legal":
            targets = legal_moves(self.position, action.get("source"))
            return {"targets": [] if self.game_over() else targets}
        elif command == "new":
            self.reset(action.get("opponent", "human"))
        elif command == "promotion-setup":
            self.reset()
            for source, target in PROMOTION_SETUP:
                self.play(source, target)
        else:
            raise ValueError("Unknown action")
        return self.view()
