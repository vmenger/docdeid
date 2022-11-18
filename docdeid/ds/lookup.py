from __future__ import annotations

import codecs
import itertools
from typing import Iterable, Iterator, Optional, Union

from docdeid.ds.ds import Datastructure
from docdeid.str.processor import StringModifier, StringProcessor, StripString


class LookupStructure(Datastructure):
    """
    Structure that contain strings, and allow efficiently checking whether a string is contained in it.

    Args:
        matching_pipeline: An optional list of :class:`.StringModifier`, that will be used to match an item
            against the structure. Implementations of :class:`.LookupStructure` must implement the logic itself.
    """

    def __init__(self, matching_pipeline: Optional[list[StringModifier]] = None) -> None:
        self.matching_pipeline = matching_pipeline

    def _apply_matching_pipeline(self, item: str) -> str:
        """
        Apply a matching pipeline to an item.

        Args:
            item: The input string.

        Returns:
            The string, modified by the matching pipeline.
        """

        if self.matching_pipeline is not None:
            for processor in self.matching_pipeline:
                item = processor.process(item)

        return item

    def has_matching_pipeline(self) -> bool:
        """
        Whether there's a matching pipeline or not.

        Returns:
            ``True`` if there is a matching pipeline, ``False`` else.
        """
        return self.matching_pipeline is not None


class LookupSet(LookupStructure):
    """
    Contains strings, that can efficiently be looked up. Additionally contains some logic for matching.

    Args:
        matching_pipeline: An optional list of :class:`.StringModifier`, that will be used to match an item
            against the set.
    """

    def __init__(self, *args, **kwargs) -> None:
        self._items: set[str] = set()
        super().__init__(*args, **kwargs)

    def clear_items(self) -> None:
        """Clear the items."""
        self._items = set()

    def add_items_from_iterable(
        self,
        items: Iterable[str],
        cleaning_pipeline: Optional[list[StringProcessor]] = None,
    ) -> None:
        """
        Add items from an iterable.

        Args:
            items: The iterable of strings.
            cleaning_pipeline: An optional cleaning pipeline applied to the strings in the iterator.
        """

        if cleaning_pipeline is not None:
            for processor in cleaning_pipeline:
                items = processor.process_items(items)

        for item in items:
            self._items.add(self._apply_matching_pipeline(item))

    def remove_items_from_iterable(self, items: Iterable[str]) -> None:
        """
        Remove items from an iterable. Respects the matching pipeline.

        Args:
            items: An iterable of the strings to be removed.
        """

        for item in items:

            item = self._apply_matching_pipeline(item)

            if item in self._items:
                self._items.remove(item)

    def add_items_from_file(
        self,
        file_path: str,
        strip_lines: bool = True,
        cleaning_pipeline: Optional[list[StringProcessor]] = None,
        encoding: str = "utf-8",
    ) -> None:
        """
        Add items from a file, line by line.

        Args:
            file_path: Full path to the file being opened.
            strip_lines: Whether to strip the lines. Applies :class:`.StripString` to each line.
            cleaning_pipeline: An optional cleaning pipeline applied to the lines in the file.
            encoding: The encoding with which to open the file.
        """

        with codecs.open(file_path, encoding=encoding) as handle:
            items = handle.read().splitlines()

        if strip_lines:
            cleaning_pipeline = [StripString()] + (cleaning_pipeline or [])

        self.add_items_from_iterable(items, cleaning_pipeline)

    def add_items_from_self(
        self,
        cleaning_pipeline: list[StringProcessor],
        replace: bool = False,
    ) -> None:
        """
        Add items from self (this items of this :class:`.LookupSet`). This can be used to do a transformation or
        replacment of the items.

        Args:
            cleaning_pipeline: A cleaning pipeline applied to the items of this set. This can also be used
                to transform the items.
            replace: Whether to replace the items with the new/transformed items.
        """

        items = self._items.copy()

        if replace:
            self.clear_items()

        self.add_items_from_iterable(items, cleaning_pipeline)

    def __len__(self) -> int:
        """
        The number of items.

        Returns:
            The number of items.
        """
        return len(self._items)

    def __contains__(self, item: str) -> bool:
        """
        Whether the lookupset contains the string item. Respects the matching pipeline.

        Args:
            item: The input string.

        Returns:
            ``True`` if the item is in the set, ``False`` otherwise.
        """

        return self._apply_matching_pipeline(item) in self._items

    def __add__(self, other: object) -> LookupSet:
        """
        Adds the items of another :class:`.LookupSet` to this one. Respects this sets matching pipeline.

        Args:
            other: Another :class:`.LookupSet` to be added.

        Returns:
            This lookupset.

        Raises:
            ValueError: When trying to add something else than a :class:`.LookupSet`.
        """

        if not isinstance(other, LookupSet):
            raise ValueError(f"Can only add LookupSet together, trying to add a {type(other.__class__)}")

        self.add_items_from_iterable(other)

        return self

    def __sub__(self, other: object) -> LookupSet:
        """
        Remove the items of another :class:`.LookupSet` from this one. Respects this sets matching pipeline.

        Args:
            other: Another :class:`.LookupSet` to be removed.

        Returns:
            This lookupset.

        Raises:
            ValueError: When trying to subtract something else than a :class:`.LookupSet`.
        """

        if not isinstance(other, LookupSet):
            raise ValueError(
                f"Can only subtract LookupSet from each other, trying to subtract a {type(other.__class__)}"
            )

        self.remove_items_from_iterable(other)

        return self

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over the items in this set.

        Returns:
            An iterator over the items in this set.
        """

        return iter(self._items)

    def items(self) -> set[str]:
        """
        Get the items in this set.

        Returns:
            The items in this set.
        """

        return self._items


class LookupTrie(LookupStructure):
    """
    Efficiently contains lists of strings (e.g. tokens), for lookup. This is done by using a trie datastructure, which
    maps each element in the sequence of strings to a next trie.

    Args:
        matching_pipeline: An optional list of :class:`.StringModifier`, that will be used to match an item
            against the Trie.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.children: dict[str, LookupTrie] = {}
        self.is_terminal = False

    def add_item(self, item: list[str]) -> None:
        """
        Add an item, i.e. a list of strings, to this Trie.

        Args:
            item: The item to be added.
        """

        if len(item) == 0:
            self.is_terminal = True

        else:

            head, tail = self._apply_matching_pipeline(item[0]), item[1:]

            if head not in self.children:
                self.children[head] = LookupTrie()

            self.children[head].add_item(tail)

    def __contains__(self, item: list[str]) -> bool:
        """
        Whether the trie contains the item. Respects the matching pipeline.

        Args:
            item: The input list of strings.

        Returns:
            ``True`` if the item is in the Trie, ``False`` otherwise.
        """

        if len(item) == 0:
            return self.is_terminal

        head, tail = self._apply_matching_pipeline(item[0]), item[1:]

        return (head in self.children) and tail in self.children[head]

    def longest_matching_prefix(self, item: list[str]) -> Union[list[str], None]:
        """
        Finds the longest matching prefix of a list of strings. This is used to find the longest matching pattern at a
        current position of a text. Respects the matching pipeline.

        Args:
            item: The input sequence of strings, of which to find the longest prefix that matches an item in this Trie.

        Returns:
            The longest matching prefix, if any, or ``None`` if no matching prefix is found.
        """

        longest_match = None
        current_node = self

        for i in itertools.count():

            if current_node.is_terminal:
                longest_match = i

            if i >= len(item) or (self._apply_matching_pipeline(item[i]) not in current_node.children):
                break

            current_node = current_node.children[self._apply_matching_pipeline(item[i])]

        return [self._apply_matching_pipeline(item) for item in item[:longest_match]] if longest_match else None
