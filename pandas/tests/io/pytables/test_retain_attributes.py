from warnings import catch_warnings

import pytest

from pandas._libs.tslibs import Timestamp

from pandas import DataFrame
from pandas import Series
from pandas import date_range
from pandas import read_hdf
import pandas._testing as tm
from pandas.tests.io.pytables.common import _maybe_remove
from pandas.tests.io.pytables.common import ensure_clean_store

pytestmark = pytest.mark.single_cpu


def test_retain_index_attributes(setup_path):
    # GH 3499, losing frequency info on index recreation
    df = DataFrame(
        {"A": Series(range(3), index=date_range("2000-1-1", periods=3, freq="H"))}
    )

    with ensure_clean_store(setup_path) as store:
        _maybe_remove(store, "data")
        store.put("data", df, format="table")

        result = store.get("data")
        tm.assert_frame_equal(df, result)

        for attr in ["freq", "tz", "name"]:
            for idx in ["index", "columns"]:
                assert getattr(getattr(df, idx), attr, None) == getattr(
                    getattr(result, idx), attr, None
                )

        # try to append a table with a different frequency
        with catch_warnings(record=True):
            df2 = DataFrame(
                {
                    "A": Series(
                        range(3), index=date_range("2002-1-1", periods=3, freq="D")
                    )
                }
            )
            store.append("data", df2)

        assert store.get_storer("data").info["index"]["freq"] is None

        # this is ok
        _maybe_remove(store, "df2")
        df2 = DataFrame(
            {
                "A": Series(
                    range(3),
                    index=[
                        Timestamp("20010101"),
                        Timestamp("20010102"),
                        Timestamp("20020101"),
                    ],
                )
            }
        )
        store.append("df2", df2)
        df3 = DataFrame(
            {"A": Series(range(3), index=date_range("2002-1-1", periods=3, freq="D"))}
        )
        store.append("df2", df3)


def test_retain_index_attributes2(tmp_path, setup_path):
    path = tmp_path / setup_path

    with catch_warnings(record=True):
        df = DataFrame(
            {"A": Series(range(3), index=date_range("2000-1-1", periods=3, freq="H"))}
        )
        df.to_hdf(path, "data", mode="w", append=True)
        df2 = DataFrame(
            {"A": Series(range(3), index=date_range("2002-1-1", periods=3, freq="D"))}
        )

        df2.to_hdf(path, "data", append=True)

        idx = date_range("2000-1-1", periods=3, freq="H")
        idx.name = "foo"
        df = DataFrame({"A": Series(range(3), index=idx)})
        df.to_hdf(path, "data", mode="w", append=True)

    assert read_hdf(path, "data").index.name == "foo"

    with catch_warnings(record=True):
        idx2 = date_range("2001-1-1", periods=3, freq="H")
        idx2.name = "bar"
        df2 = DataFrame({"A": Series(range(3), index=idx2)})
        df2.to_hdf(path, "data", append=True)

    assert read_hdf(path, "data").index.name is None
