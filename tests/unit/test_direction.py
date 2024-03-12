import pytest

from docdeid.direction import Direction


class TestDirection:
    def test_basics(self):
        assert Direction.LEFT != Direction.RIGHT
        assert Direction.LEFT.opposite == Direction.RIGHT
        assert Direction.RIGHT.opposite == Direction.LEFT

    def test_parsing(self):
        assert Direction.from_string("left") == Direction.LEFT
        assert Direction.from_string("Left") == Direction.LEFT
        assert Direction.from_string("LEFT") == Direction.LEFT
        assert Direction.from_string("right") == Direction.RIGHT
        assert Direction.from_string("Right") == Direction.RIGHT
        assert Direction.from_string("RIGHT") == Direction.RIGHT

    def test_parsing_failure(self):
        with pytest.raises(ValueError, match="Invalid direction: 'down'"):
            Direction.from_string("down")
        with pytest.raises(ValueError, match="Invalid direction: ' left'"):
            Direction.from_string(" left")

    def test_iteration(self):
        assert list(Direction.RIGHT.iter([])) == []
        assert list(Direction.LEFT.iter([])) == []
        assert list(Direction.RIGHT.iter([1, 2, "three"])) == [1, 2, "three"]
        assert list(Direction.LEFT.iter([1, 2, "three"])) == ["three", 2, 1]
