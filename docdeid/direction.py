from __future__ import annotations

from enum import IntEnum
from typing import Iterable, Sequence, TypeVar

T = TypeVar("T")


class Direction(IntEnum):
    """Direction in text -- either left or right."""

    LEFT = -1
    RIGHT = 1

    @property
    def opposite(self) -> Direction:
        """The opposite direction to this."""
        return Direction(-self)

    @staticmethod
    def from_string(val: str) -> Direction:
        """Parses a Direction from a string (case insensitive)."""
        try:
            return Direction[val.upper()]
        except KeyError as key_error:
            raise ValueError(f"Invalid direction: '{val}'") from key_error

    def iter(self, seq: Sequence[T]) -> Iterable[T]:
        """
        Returns an iterator over the given sequence that traverses it in this direction.

        Args:
            seq: sequence to iterate over
        """
        if self is Direction.RIGHT:
            return seq
        return reversed(seq)
