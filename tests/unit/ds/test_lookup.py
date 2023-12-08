import pytest

from docdeid.ds.lookup import LookupSet, LookupStructure, LookupTrie
from docdeid.str.processor import LowercaseString, StripString


@pytest.fixture
def lowercase_proc():
    return LowercaseString()


@pytest.fixture
def strip_proc():
    return StripString()


class TestLookupStructure:
    def test_pipeline(self, lowercase_proc, strip_proc):
        pipe = [lowercase_proc, strip_proc]
        struct = LookupStructure(matching_pipeline=pipe)

        assert struct._apply_matching_pipeline(" Test") == "test"

    def test_pipeline_empty(self):
        struct = LookupStructure()

        assert struct._apply_matching_pipeline(" Test") == " Test"


class TestLookupSet:
    def test_create_empty_set(self):
        lookup_set = LookupSet()

        assert len(lookup_set) == 0

    def test_add_items_from_iterable(self):
        names = ["John", "Mary", "Susan"]

        lookup_set = LookupSet()
        lookup_set.add_items_from_iterable(items=names)

        for name in names:
            assert name in lookup_set

    def test_add_items_from_self(self, lowercase_proc):
        names = ["John", "Mary", "Susan"]

        lookup_set = LookupSet()
        lookup_set.add_items_from_iterable(items=names)
        lookup_set.add_items_from_self(cleaning_pipeline=[lowercase_proc])

        for name in names:
            assert lowercase_proc.process(name) in lookup_set

    def test_add_items_from_file(self):
        lookup_set = LookupSet()
        lookup_set.add_items_from_file(file_path="tests/data/name_list.txt")

        assert "John" in lookup_set
        assert "Mary" in lookup_set
        assert "Susan" in lookup_set

    def test_len(self):
        lookup_set = LookupSet()
        lookup_set.add_items_from_iterable(items=["a", "b", "c"])

        assert len(lookup_set) == 3

    def test_add_sets(self):
        # a
        first_items = ["a", "b", "c"]
        set1 = LookupSet()
        set1.add_items_from_iterable(items=first_items)

        second_items = ["c", "d", "e"]
        set2 = LookupSet()
        set2.add_items_from_iterable(items=second_items)

        # a
        set1 += set2

        # a
        assert len(set1) == 5
        assert len(set2) == 3

        for item in first_items:
            assert item in set1

        for item in second_items:
            assert item in set1
            assert item in set2

    def test_subtract_sets(self):
        # a
        first_items = ["a", "b", "c", "d", "e"]
        set1 = LookupSet()
        set1.add_items_from_iterable(items=first_items)

        second_items = ["c", "d", "e"]
        set2 = LookupSet()
        set2.add_items_from_iterable(items=second_items)

        # a
        set1 -= set2

        # a
        assert len(set1) == 2
        assert len(set2) == 3

        assert "a" in set1
        assert "b" in set1

        for item in second_items:
            assert item not in set1
            assert item in set2

    def test_iterator(self):
        items = {"red", "blue", "green"}
        lookup_set = LookupSet()
        lookup_set.add_items_from_iterable(items=items)

        items_in_set = {item for item in lookup_set}

        assert items == items_in_set

    def test_matching_pipeline_add(self, lowercase_proc):
        items = {"John", "Mary", "Bob"}

        lookup_set = LookupSet(matching_pipeline=[lowercase_proc])
        lookup_set.add_items_from_iterable(items=items)

        for item in items:
            assert item in lookup_set
            assert lowercase_proc.process(item) in lookup_set

    def test_matching_pipeline_remove(self, lowercase_proc):
        items = {"John", "Mary"}
        lookup_set = LookupSet(matching_pipeline=[lowercase_proc])
        lookup_set.add_items_from_iterable(items=items)

        lookup_set.remove_items_from_iterable(items=["john"])

        assert "john" not in lookup_set
        assert "John" not in lookup_set
        assert "Mary" in lookup_set
        assert "mary" in lookup_set

    def test_matching_pipeline_with_addition(self, lowercase_proc):
        items = {"John", "Mary", "Bob"}
        lookup_set = LookupSet(matching_pipeline=[lowercase_proc])
        lookup_set.add_items_from_iterable(items=items)

        lookup_set += LookupSet()

        for item in items:
            assert item in lookup_set
            assert lowercase_proc.process(item) in lookup_set

    def test_matching_pipeline_with_subtraction(self, lowercase_proc):
        items = {"John", "Mary"}
        lookup_set = LookupSet(matching_pipeline=[lowercase_proc])
        lookup_set.add_items_from_iterable(items=items)

        set2 = LookupSet()
        set2.add_items_from_iterable(items=["mary"])

        lookup_set -= set2

        assert "John" in lookup_set
        assert "john" in lookup_set
        assert "Mary" not in lookup_set
        assert "mary" not in lookup_set


class TestLookupTrie:
    def test_empty_trie(self):
        trie = LookupTrie()

        assert [] not in trie
        assert ["these", "are", "some", "words"] not in trie

    def test_create_trie(self):
        trie = LookupTrie()
        items = ["these", "are", "some", "words"]

        trie.add_item(item=items)

        assert items in trie

    def test_empty_sequence(self):
        trie = LookupTrie()
        trie.add_item(item=[])

        assert [] in trie

    def test_longest_matching_prefix_1(self):
        trie = LookupTrie()

        assert trie.longest_matching_prefix(item=[]) is None
        assert trie.longest_matching_prefix(item=["a"]) is None

    def test_longest_matching_prefix_2(self):
        trie = LookupTrie()
        trie.add_item(item=["a"])
        trie.add_item(item=["a", "b", "c"])

        assert trie.longest_matching_prefix(item=[]) is None
        assert trie.longest_matching_prefix(item=["a"]) == ["a"]
        assert trie.longest_matching_prefix(item=["a", "b"]) == ["a"]
        assert trie.longest_matching_prefix(item=["a", "b", "c"]) == ["a", "b", "c"]
        assert trie.longest_matching_prefix(item=["a", "b", "c", "d"]) == [
            "a",
            "b",
            "c",
        ]

    def test_longest_matching_prefix_3(self):
        trie = LookupTrie()
        trie.add_item(item=["a", "b"])
        trie.add_item(item=["cat", "dog"])

        assert trie.longest_matching_prefix(item=["a"]) is None
        assert trie.longest_matching_prefix(item=["a", "b"]) == ["a", "b"]
        assert trie.longest_matching_prefix(item=["cat"]) is None
        assert trie.longest_matching_prefix(item=["cat", "dog"]) == ["cat", "dog"]

    def test_trie_with_matching_pipeline_contains(self, lowercase_proc):
        trie = LookupTrie(matching_pipeline=[lowercase_proc])
        trie.add_item(item=["a", "b"])
        trie.add_item(item=["A", "B"])

        assert ["a", "b"] in trie
        assert ["a", "B"] in trie
        assert ["A", "b"] in trie
        assert ["A", "B"] in trie

    def test_trie_with_matching_pipeline_prefix(self, lowercase_proc):
        trie = LookupTrie(matching_pipeline=[lowercase_proc])
        trie.add_item(item=["a", "b"])
        trie.add_item(item=["A", "B"])

        assert trie.longest_matching_prefix(item=["a", "b", "c"]) == ["a", "b"]
        assert trie.longest_matching_prefix(item=["a", "B", "C"]) == ["a", "b"]
        assert trie.longest_matching_prefix(item=["A", "B", "C"]) == ["a", "b"]

    def test_trie_with_start_i(self):
        trie = LookupTrie()
        trie.add_item(item=["a", "b"])
        trie.add_item(item=["cat", "dog"])

        assert trie.longest_matching_prefix(item=["a", "b"], start_i=0) == ["a", "b"]
        assert trie.longest_matching_prefix(item=["a", "b"], start_i=1) is None
        assert trie.longest_matching_prefix(
            item=["horse", "cat", "dog"], start_i=1
        ) == ["cat", "dog"]
