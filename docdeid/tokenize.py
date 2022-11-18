from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator, Literal, Optional


@dataclass(frozen=True)
class Token:
    """A token is an atomic part of a text, as determined by a tokenizer."""

    text: str
    """ The text. """

    start_char: int
    """ The start char. """

    end_char: int
    """ The end char. """

    _previous_token: Optional[Token] = field(default=None, repr=False, compare=False)
    """ The previous token. Note that this does not have to be the literal next token in the text, the logic is
    dictated by :meth:`.Tokenizer._previous_token`, which could for example take the previous alpha token. """

    _next_token: Optional[Token] = field(default=None, repr=False, compare=False)
    """ The next token. Note that this does not have to be the literal next token in the text, the logic is
    dictated by :meth:`.Tokenizer._next_token`, which could for example take the next alpha token. """

    def __post_init__(self) -> None:

        if len(self.text) != (self.end_char - self.start_char):
            raise ValueError("The span does not match the length of the text.")

    def set_previous_token(self, token: Optional[Token]) -> None:
        """
        Set the previous token, in a linked list fashion.

        Args:
            token: The previous :class:`.Token`.
        """
        object.__setattr__(self, "_previous_token", token)

    def set_next_token(self, token: Optional[Token]) -> None:
        """
        Set the next token, in a linked list fashion.

        Args:
            token: The next :class:`.Token`.
        """
        object.__setattr__(self, "_next_token", token)

    def _get_linked_token(self, num: int, attr: Literal["_previous_token", "_next_token"]) -> Optional[Token]:
        """
        Helper method for getting previous/next tokens, possibly more than one neighbour.

        Args:
            num: Searches the ``num``-th token to the left/right.
            attr: Either ``_previous_token`` or ``_next_token``, depending on which to look for.

        Returns:
            The token ``num`` positions to the left/right, if any, or ``None`` otherwise.
        """

        token = self

        for _ in range(num):
            token = getattr(token, attr)

            if token is None:
                return None

        return token

    def previous(self, num: int = 1) -> Optional[Token]:
        """
        Get the previous :class:`.Token`, if any.

        Args:
            num: Searches the ``num``-th token to the left.

        Returns:
            The token ``num`` positions to the left, if any, or ``None`` otherwise.
        """
        return self._get_linked_token(num=num, attr="_previous_token")

    def next(self, num: int = 1) -> Optional[Token]:
        """
        Get the next :class:`.Token`, if any.

        Args:
            num: Searches the ``num``-th token to the right.

        Returns:
            The token ``num`` positions to the right, if any, or ``None`` otherwise.
        """
        return self._get_linked_token(num=num, attr="_next_token")

    def __len__(self) -> int:
        """
        The length of the text.

        Returns:
            The length of the text.
        """
        return len(self.text)


class TokenList:
    """
    Contains a sequence of tokens, along with some lookup logic.

    Args:
        tokens: The input tokens (must be final).
    """

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._words: Optional[set[str]] = None
        self._text_to_tokens: Optional[defaultdict[str, list[Token]]] = None

    def _init_token_lookup(self) -> tuple[set[str], defaultdict[str, list[Token]]]:
        """
        Initialize token lookup structures.

        Returns:
            A set of words (``string``), and a mapping of word (``string``) to one or more :class:`.Token`.
        """

        words = set()
        text_to_tokens = defaultdict(list)

        for token in self._tokens:
            words.add(token.text)
            text_to_tokens[token.text].append(token)

        return words, text_to_tokens

    def token_lookup(self, lookup_values: set[str]) -> set[Token]:
        """
        Find the tokens in this set, which have matching text to any of the texts given as input.

        Args:
            lookup_values: The string values to look for matching tokens.

        Returns:
            A set of :class:`.Token` matching the input.
        """

        # Lazy init
        if (self._words is None) or (self._text_to_tokens is None):
            self._words, self._text_to_tokens = self._init_token_lookup()

        tokens = set()
        texts = lookup_values.intersection(self._words)

        for text in texts:
            tokens.update(self._text_to_tokens[text])

        return tokens

    def __iter__(self) -> Iterator[Token]:
        """
        An iterator over the tokens.

        Returns:
            An iterator over the tokens.
        """
        return iter(self._tokens)

    def __len__(self) -> int:
        """
        The number of tokens.

        Returns:
            The number of tokens.
        """
        return len(self._tokens)

    def __getitem__(self, index: int) -> Token:
        """
        Get :class:`.Token` at index.

        Args:
            index: The requested index.

        Returns:
            The :class:`.Token` at the specified index.
        """
        return self._tokens[index]

    def __eq__(self, other: object) -> bool:
        """
        Check if two :class:`.TokenList` are equal, by matching the tokens.

        Args:
            other: The other :class:`.TokenList`.

        Returns:
            ``True`` if the tokens exactly match, ``False`` otherwise. Does not check text equality but
                :class:`.Token` equality.

        Raises:
            ValueError: When trying to check equality of something different than a :class:`.TokenList`.
        """

        if not isinstance(other, TokenList):
            raise ValueError(f"Cannot compare {self.__class__} to {other.__class__}")

        return self._tokens == other._tokens


class Tokenizer(ABC):
    """
    Abstract class for tokenizers, which split a text up in its smallest parts called tokens. Implementations should
    implement :meth:`.Tokenizer._split_text`.

    Args:
        link_tokens: Whether to link the produced tokens by calling the :meth:`.Token.set_previous_token` and
            :meth:`.Token.set_next_token` methods. If true, it uses the logic implemented in the
            :meth:`.Tokenizer._previous_token` and :meth:`.Tokenizer._next_token` methods.
    """

    def __init__(self, link_tokens: bool = True) -> None:
        self.link_tokens = link_tokens

    @staticmethod
    def _previous_token(position: int, tokens: list[Token]) -> Optional[Token]:
        """
        Determines the logic for getting the previous token. By default, just the literal neighbour.

        Args:
            position: The position to determine the neighbour for.
            tokens: The list of tokens.

        Returns:
            The previous token, if any, or ``None`` otherwise.
        """

        if position == 0:
            return None

        return tokens[position - 1]

    @staticmethod
    def _next_token(position: int, tokens: list[Token]) -> Optional[Token]:
        """
        Determines the logic for getting the next token. By default, just the literal neighbour.

        Args:
            position: The position to determine the neighbour for.
            tokens: The list of tokens.

        Returns:
            The next token, if any, or ``None`` otherwise.
        """

        if position == len(tokens) - 1:
            return None

        return tokens[position + 1]

    @abstractmethod
    def _split_text(self, text: str) -> list[Token]:
        """
        Abstract method for splitting the text. Instantiations of :class:`.Tokenizer` should implement this.

        Args:
            text: The input text.

        Returns: A list of tokens, as determined by the tokenizer logic.
        """

    def _link_tokens(self, tokens: list[Token]) -> None:
        """
        Link the tokens that are obtained by splitting the text, based on the internal logic implemented in
        :meth:`.Tokenizer._previous_token` and :meth:`.Tokenizer._next_token`.

        Args:
            tokens: The list of input tokens.
        """

        for i, token in enumerate(tokens):
            previous_token = self._previous_token(position=i, tokens=tokens)
            token.set_previous_token(previous_token)

            next_token = self._next_token(position=i, tokens=tokens)
            token.set_next_token(next_token)

    def tokenize(self, text: str) -> TokenList:
        """
        Tokenize a text, based on the logic implemented in :meth:`.Tokenizer._split_text`.

        Args:
            text: The input text.

        Returns:
            A :class:`.TokenList`, containing the created tokens.
        """

        tokens = self._split_text(text)

        if self.link_tokens:
            self._link_tokens(tokens)

        return TokenList(tokens)


class SpaceSplitTokenizer(Tokenizer):
    """
    Tokenizes based on splitting on whitespaces.

    Whitespaces themselves are not included as tokens.
    """

    def _split_text(self, text: str) -> list[Token]:

        return [
            Token(text=match.group(0), start_char=match.start(), end_char=match.end())
            for match in re.finditer(r"[^\s]+", text)
        ]


class WordBoundaryTokenizer(Tokenizer):
    """
    Tokenizes based on word boundary.

    Whitespaces and similar characters are included as tokens.
    """

    def _split_text(self, text: str) -> list[Token]:

        tokens = []
        matches = [*re.finditer(r"\b", text)]

        for start_match, end_match in zip(matches, matches[1:]):

            start_char = start_match.span(0)[0]
            end_char = end_match.span(0)[0]

            tokens.append(Token(text=text[start_char:end_char], start_char=start_char, end_char=end_char))

        return tokens
