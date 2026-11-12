"""Build test boards from readable placements and check they hold valid pieces."""

from game import coordinates

PIECES = {side + kind for side in "wb" for kind in "KQRBNP"}


def assert_valid_board(board: dict[str, str]) -> None:
    """A test board must be a position that could occur: real squares and pieces,
    exactly one king per side, kings not touching, no pawns on the first or last rank."""
    for square, piece in board.items():
        coordinates(square)
        assert piece in PIECES, f"{piece!r} on {square} is not a piece"
        if piece[1] == "P":
            assert square[1] not in "18", f"pawn on {square}"
    kings = {side: [s for s, p in board.items() if p == side + "K"] for side in "wb"}
    assert len(kings["w"]) == 1, "need one white king"
    assert len(kings["b"]) == 1, "need one black king"
    (wx, wy), (bx, by) = coordinates(kings["w"][0]), coordinates(kings["b"][0])
    assert max(abs(wx - bx), abs(wy - by)) > 1, "kings cannot touch"


def board(*placements: str) -> dict[str, str]:
    """board("wK e1", "bK e8", "wB c1") -> {"e1": "wK", "e8": "bK", "c1": "wB"}"""
    result: dict[str, str] = {}
    for placement in placements:
        piece, square = placement.split()
        assert square not in result, f"two pieces on {square}"
        result[square] = piece
    assert_valid_board(result)
    return result
