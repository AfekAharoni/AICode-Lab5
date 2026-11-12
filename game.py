"""Movement rules for the lab's chess variant.

Check, checkmate and stalemate follow standard chess. There is no castling and no
en passant. When neither side has enough material to checkmate, the game is drawn
automatically. Threefold repetition and the fifty-move rule are not implemented.
"""

from typing import Any

# A square such as "e2" maps to a piece such as "wP" (side w/b + kind KQRBNP).
Board = dict[str, str]
# [board, side to move]. A two-item list whose items differ in type, hence Any.
Position = list[Any]

FILES = "abcdefgh"
SQUARE_LENGTH = 2  # file letter + rank digit
BACK_ROW = "RNBQKBNR"


def new_position() -> Position:
    board = {}
    for file, piece in zip(FILES, BACK_ROW):
        board[file + "1"] = "w" + piece
        board[file + "2"] = "wP"
        board[file + "7"] = "bP"
        board[file + "8"] = "b" + piece
    return [board, "w"]


def copy_position(position: Position) -> Position:
    """Copy the board and side to move."""
    return [position[0].copy(), position[1]]


def coordinates(square: object) -> tuple[int, int]:
    if not isinstance(square, str) or len(square) != SQUARE_LENGTH:
        raise ValueError("Expected a square such as e2")
    if square[0] not in FILES or square[1] not in "12345678":
        raise ValueError("Square is outside the board")
    return FILES.index(square[0]), int(square[1]) - 1


def other(side: str) -> str:
    return "b" if side == "w" else "w"


def in_check(board: Board, side: str) -> bool:
    king = next((square for square, piece in board.items() if piece == side + "K"), None)
    return king is not None and any(
        king in reachable(board, square) for square, piece in board.items() if piece[0] != side
    )


def status(position: Position) -> str | None:
    """Return "check", "checkmate", "stalemate", or None for the side to move."""
    board, turn = position[:2]
    check = in_check(board, turn)
    if any(legal_moves(position, square) for square, piece in board.items() if piece[0] == turn):
        return "check" if check else None
    return "checkmate" if check else "stalemate"


def insufficient_material(board: Board) -> bool:
    """True when neither side can ever checkmate.

    That is: kings alone, kings with a single bishop or knight, or kings with bishops
    that all stand on squares of one colour.
    """
    others = [(square, piece[1]) for square, piece in board.items() if piece[1] != "K"]
    if any(kind not in ("B", "N") for _, kind in others):
        return False
    if len(others) <= 1:
        return True
    if all(kind == "B" for _, kind in others):
        return len({sum(coordinates(square)) % 2 for square, _ in others}) == 1
    return False


def winner(position: Position) -> str | None:
    if status(position) == "checkmate":
        return "White" if position[1] == "b" else "Black"
    return None


def legal_moves(position: Position, source: object) -> list[str]:
    """Moves for the side to move that do not leave its own king in check."""
    coordinates(source)
    assert isinstance(source, str)  # coordinates() rejects anything else
    board, turn = position[:2]
    piece = board.get(source)
    if not piece or piece[0] != turn:
        return []
    targets = []
    for target in reachable(board, source):
        trial = board.copy()
        trial[target] = trial.pop(source)
        if not in_check(trial, turn):
            targets.append(target)
    return targets


def reachable(board: Board, source: str) -> list[str]:
    """Squares the piece on source attacks or can move to, ignoring check."""
    piece = board[source]
    turn = piece[0]
    x, y = coordinates(source)
    targets = []
    for tx in range(8):
        for ty in range(8):
            target = FILES[tx] + str(ty + 1)
            occupant = board.get(target)
            if target == source or (occupant and occupant[0] == turn):
                continue
            dx, dy = tx - x, ty - y
            kind = piece[1]
            allowed = False
            if kind == "P":
                direction = 1 if turn == "w" else -1
                home = 1 if turn == "w" else 6
                allowed = (
                    (dx == 0 and dy == direction and not occupant)
                    or (
                        dx == 0
                        and dy == 2 * direction
                        and y == home
                        and not occupant
                        and FILES[x] + str(y + direction + 1) not in board
                    )
                    or (abs(dx) == 1 and dy == direction and bool(occupant))
                )
            elif kind == "N":
                allowed = (abs(dx), abs(dy)) in ((1, 2), (2, 1))
            elif kind == "K":
                allowed = max(abs(dx), abs(dy)) == 1
            else:
                diagonal = abs(dx) == abs(dy)
                straight = dx == 0 or dy == 0
                allowed = (
                    (kind == "B" and diagonal)
                    or (kind == "R" and straight)
                    or (kind == "Q" and (diagonal or straight))
                )
                if allowed:
                    sx = (dx > 0) - (dx < 0)
                    sy = (dy > 0) - (dy < 0)
                    for step in range(1, max(abs(dx), abs(dy))):
                        intermediate = FILES[x + step * sx] + str(y + step * sy + 1)
                        if intermediate in board:
                            allowed = False
                            break
            if allowed:
                targets.append(target)
    return targets


PROMOTION_PIECES = ("Q", "R", "B", "N")


def promotes(position: Position, source: str, target: str) -> bool:
    piece = position[0].get(source)
    return bool(piece) and piece[1] == "P" and target[1] in "18"


def move(position: Position, source: str, target: str, promotion: str | None = None) -> str:
    """Apply a move in place. Return a short move label.

    A pawn reaching the last rank needs promotion: "Q", "R", "B" or "N".
    """
    coordinates(target)
    if target not in legal_moves(position, source):
        raise ValueError("That move is not allowed")
    if promotes(position, source, target):
        if promotion not in PROMOTION_PIECES:
            raise ValueError("Choose a queen, rook, bishop or knight to promote to")
        chosen = promotion
    elif promotion is not None:
        raise ValueError("Only a pawn reaching the last rank promotes")
    else:
        chosen = ""
    board = position[0]
    piece = board.pop(source)
    captured = board.get(target)
    board[target] = piece
    if chosen:
        board[target] = piece[0] + chosen
    position[1] = other(position[1])
    suffix = {"check": "+", "checkmate": "#"}.get(status(position) or "", "")
    label = "=" + chosen if chosen else ""
    return source + ("x" if captured else "-") + target + label + suffix
