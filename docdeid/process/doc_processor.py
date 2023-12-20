from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Iterator, Optional, Union

from docdeid.document import Document


class DocProcessor(ABC):  # pylint: disable=R0903
    """Something that processes a document."""

    @abstractmethod
    def process(self, doc: Document, **kwargs) -> None:
        """
        Process the document.

        Args:
            doc: The document as input.
            **kwargs: Any other settings.
        """


class DocProcessorGroup:
    """
    A group of :class:`.DocProcessor`, that executes the containing processors in order.

    A :class:`.DocProcessorGroup` can itself be part of a :class:`.DocProcessorGroup`.
    """

    def __init__(self) -> None:
        self._processors: OrderedDict[
            str, Union[DocProcessor | DocProcessorGroup]
        ] = OrderedDict()

    def get_names(self, recursive: bool = True) -> list[str]:
        """
        Get the names of all document processors.

        Args:
            recursive: Whether to recurse on any contained :class:`.DocProcessorGroup`.

        Returns:
            The names of all document processors.
        """

        names = []

        for name, processor in self._processors.items():

            names.append(name)

            if recursive and isinstance(processor, DocProcessorGroup):
                names += processor.get_names(recursive)

        return names

    def add_processor(
        self,
        name: str,
        processor: Union[DocProcessor, "DocProcessorGroup"],
        position: Optional[int] = None,
    ) -> None:
        """
        Add a document processor to the group.

        Args:
            name: The name of the processor.
            processor: The processor or processor group.
            position: The position at which to insert it. Will append if left
            unspecified.
        """

        if position is None:
            self._processors[name] = processor
            return

        new_processors = OrderedDict()

        for i, (existing_name, existing_processor) in enumerate(
            self._processors.items()
        ):

            if i == position:
                new_processors[name] = processor

            new_processors[existing_name] = existing_processor

        self._processors = new_processors

    def remove_processor(self, name: str) -> None:
        """
        Remove a processor from the group.

        Args:
            name: The name of the processor.
        """
        del self._processors[name]

    def __getitem__(self, name: str) -> Union[DocProcessor, "DocProcessorGroup"]:
        """
        Get a document processor by name.

        Args:
            name: The name of the document processor.

        Returns:
            The document processor.
        """

        return self._processors[name]

    def process(
        self,
        doc: Document,
        enabled: Optional[set[str]] = None,
        disabled: Optional[set[str]] = None,
    ) -> None:
        """
        Process a document, by passing it to this group's processors.

        Args:
            doc: The document to be processed.
            enabled: A set of strings, indicating which document processors to run for
                this document. By default, all document processors are used. In case
                of nested, it's necessary to supply both the name of the processor
                group, and all of its containing processors (or a subset thereof).
            disabled: A set of strings, indicating which document processors not to
                run for this document. Cannot be used together with `enabled`.
        """

        if (enabled is not None) and (disabled is not None):
            raise RuntimeError("Cannot use enabled and disabled simultaneously")

        for name, proc in self._processors.items():

            if (enabled is not None) and (name not in enabled):
                continue

            if (disabled is not None) and (name in disabled):
                continue

            if isinstance(proc, DocProcessor):
                proc.process(doc)
            elif isinstance(proc, DocProcessorGroup):
                proc.process(doc, enabled=enabled, disabled=disabled)

    def __iter__(self) -> Iterator:

        return iter(self._processors.items())
