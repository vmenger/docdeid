from abc import abstractmethod

from docdeid.str.processor import ReplaceValue, StringModifier


class Expander(str):
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
        initial = {item}
        if len(item) < self.min_length:
            return initial
        return {item} + {m.process(item) for m in self.str_modifiers}


if __name__ == "__main__":
    str_modifier = ReplaceValue("a", "b")
    expander = MinimumLengthExpander(5, [str_modifier])

    assert expander.expand_item("a") == {"a"}
    assert expander.expand_item("aaaa") == {"aaaaa"}
    assert expander.expand_item("aaaaa") == {"bbbbb"}
