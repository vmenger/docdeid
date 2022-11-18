import pytest

from docdeid.ds.ds import Datastructure, DsCollection


class TestDsCollection:
    def test_ds_collection(self):

        ds = Datastructure()
        dsc = DsCollection()

        dsc["name"] = ds

        assert dsc["name"] is ds

    def test_ds_collection_remove(self):

        ds = Datastructure()
        dsc = DsCollection()

        dsc["name"] = ds
        del dsc["name"]

        with pytest.raises(KeyError):
            _ = dsc["name"]
