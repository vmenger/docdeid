from abc import ABC, abstractmethod

from docdeid.str.processor import StringModifier


class Expander(ABC):
    """Abstract class for string expansion."""

    @abstractmethod
    def expand_item(self, item: str) -> list[str]:
        """
        Expand a string into a list of strings that contains the original and possibly additional strings.

        Args:
            items: The input item.

        Returns:
            The expanded items.
        """


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
