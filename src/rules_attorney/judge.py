"""The judge, scoring a run's rulings against the gold set."""


def flag_correct(status: str, ambiguous: bool) -> bool:
    """Whether the model's flag is right: settled unflagged, anything else flagged."""
    expected = status != "settled"
    return ambiguous == expected
