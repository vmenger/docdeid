from abc import ABC, abstractmethod
from typing import Optional

from docdeid.document import Document, MetaData
from docdeid.tokenize import Token


class TokenPattern(ABC):
    """
    A pattern that can be applied to a token, and possibly its neighbours, by matching the :class:`.Token` text.

    Args:
        tag: The tag that the annotations should be tagged with.
    """

    def __init__(self, tag: str) -> None:
        self.tag = tag

    @staticmethod
    def doc_precondition(doc: Document) -> bool:
        """
        Use this to check if the pattern is applicable to a document (e.g. check if some piece of metadata is included.
        By default returns ``True``.

        Args:
            doc: The :class`.Document` the pattern will be applied to.

        Returns:
            ``True`` if applicable, ``False`` otherwise.
        """

        return True

    @staticmethod
    def token_precondition(token: Token) -> bool:
        """
        Use this to check if the pattern is applicable to a token (e.g. check if it has neighbours). By default returns
        ``True``.

        Args:
            token: The :class:`.Token` the pattern will be applied to.

        Returns:
            ``True`` if applicable, ``False`` otherwise.
        """

        return True

    @abstractmethod
    def match(self, token: Token, metadata: MetaData) -> Optional[tuple[Token, Token]]:
        """
        Check if the token provided matches this pattern. Instantiations of :class:`.TokenPattern` should implement
        the logic of the pattern in this method. For example, by checking if the text is lowercase, titlecase, longer
        than a certain number of characters, etc. The :class:`.Token` neighbours may be accessible by
        :meth:`.Token.previous` and :meth:`.Token.next`, if linked by the tokenizer.

        Args:
            token: The token.
            metadata: The metadata.

        Returns:
            A tuple with the start and end :class:`.Token` if matching, or ``None`` if no match is possible.
        """
