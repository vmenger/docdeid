from abc import ABC, abstractmethod
from typing import Iterable

from docdeid.str.processor import StringModifier


class Expander(ABC):
    """Abstract class for string expansion."""

    @abstractmethod
    def expand_item(self, item: str) -> set[str]:
        """
        Expand a string into a list of strings that contains the original and possibly additional strings.

        Args:
            items: The input item.

        Returns:
            The expanded items.
        """

    def expand_item_iterable(self, items: Iterable[str]) -> set[str]:
        """
        Expand a set of strings into a set of strings that contains the original and possibly additional strings.

        Args:
            words: The input set of strings.

        Returns:
            The expanded set of strings.
        """
        return set.union(*(self.expand_item(item) for item in items))

    def get_expansion_to_original_dict(self, items: Iterable[str]) -> dict[str, str]:
        """Expand a set of strings into a dictionary where the keys are results from expand_item and values the original text."""

        # This can get overwritten if different original texts map to the same expansion due to multiple operations...
        result_dict = {}
        for item in items:
            for expansion in self.expand_item(item):
                result_dict[expansion] = item
        return result_dict


class MinimumLengthExpander(Expander):
    """Expands a string by applying the lists of string processors. These are only applied to tokens whose length >= minimum length"""

    def __init__(
        self, str_modifiers: list[StringModifier], min_length: int = 5
    ) -> None:
        self.min_length = min_length
        self.str_modifiers = str_modifiers

    def expand_item(self, item: str) -> set[str]:
        """
        Expand a string by adding versions for each string processor if the length surpasses the minimum.

        Args:
            item: The input item.

        Returns:
            The expanded items.
        """
        result = {item}
        if len(item) < self.min_length:
            return result
        result.update(m.process(item) for m in self.str_modifiers)
        return result
