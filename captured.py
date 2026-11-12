"""The captured-pieces sidebar."""


def captured_pieces(captures: list[str | None]) -> list[str]:
    """Pieces taken so far, sorted, from the per-move log (None for a non-capture).

    Each entry is the piece as it stood on the target square when it was taken, so a
    promoted piece is shown with its promoted type and a promotion alone adds nothing.
    """
    return sorted(piece for piece in captures if piece is not None)
