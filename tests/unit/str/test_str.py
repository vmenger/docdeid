from docdeid.str.processor import (
    FilterByLength,
    LowercaseString,
    RemoveNonAsciiCharacters,
    ReplaceNonAsciiCharacters,
    ReplaceValue,
    ReplaceValueRegexp,
    StripString,
)


class TestStringModifier:
    def test_lowercase_string(self):
        proc = LowercaseString()

        assert proc.process("albert") == "albert"
        assert proc.process("Albert") == "albert"

    def test_strip_string(self):
        proc = StripString()

        assert proc.process("test") == "test"
        assert proc.process(" test") == "test"
        assert proc.process("test\n") == "test"

    def test_remove_non_ascii(self):
        proc = RemoveNonAsciiCharacters()

        assert proc.process("test") == "test"
        assert proc.process("Renée") == "Rene"
        assert proc.process("áóçëū") == ""

    def test_replace_non_ascii(self):
        proc = ReplaceNonAsciiCharacters()

        assert proc.process("test") == "test"
        assert proc.process("Renée") == "Renee"
        assert proc.process("áóçëū") == "aoceu"

    def test_replace_value(self):
        proc = ReplaceValue(find_value="cat", replace_value="dog")

        assert proc.process("test") == "test"
        assert (
            proc.process("My favorite animal is a cat") == "My favorite animal is a dog"
        )
        assert (
            proc.process("My favorite animal is a dog") == "My favorite animal is a dog"
        )

    def test_replace_value_regexp(self):
        proc = ReplaceValueRegexp(find_value=r"\d+", replace_value="number")

        assert proc.process("test") == "test"
        assert proc.process("one is smaller than two") == "one is smaller than two"
        assert proc.process("1 is smaller than 2") == "number is smaller than number"


class TestStringFilter:
    def test_filter_by_length(self):
        proc = FilterByLength(min_len=5)

        assert not proc.filter("")
        assert not proc.filter("test")
        assert proc.filter("12345")
        assert proc.filter("longer phrase")
