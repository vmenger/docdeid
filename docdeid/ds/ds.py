from abc import ABC


class Datastructure(ABC):  # pylint: disable=R0903
    """Something that holds data in an efficient way."""


class DsCollection(dict[str, Datastructure]):
    """
    A collection of datastructures.

    Directly inherits from ``dict``.
    """
