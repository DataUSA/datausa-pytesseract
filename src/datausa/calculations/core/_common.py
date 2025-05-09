from collections.abc import Sequence
from typing import Annotated, Any

from pydantic import BeforeValidator


def parse_qs_lists(value: Any) -> Any:
    """Transform a comma-separated string value into a list of strings."""
    if isinstance(value, str):
        value = value.split(",")
    if isinstance(value, Sequence):
        value = {item.strip() for token in value for item in token.split(",")}
    return value


def parse_qs_cuts(value: Any) -> Any:
    """Transform a colon separated dict string into a cut-members mapping."""
    if isinstance(value, str):
        value = value.split(";")
    if isinstance(value, Sequence):
        value = {
            key: set(value.split(","))
            for key, value in (
                tuple(token.split(":", maxsplit=1)) for item in value for token in item.split(";")
            )
        }
    return value


CutMapping = Annotated[dict[str, set[str]], BeforeValidator(parse_qs_cuts)]
CommaStrList = Annotated[set[str], BeforeValidator(parse_qs_lists)]
