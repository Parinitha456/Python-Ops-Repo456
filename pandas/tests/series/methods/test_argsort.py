import numpy as np
import pytest

from pandas import (
    Series,
    Timestamp,
    isna,
)
import pandas._testing as tm


class TestSeriesArgsort:
    def test_argsort_axis(self):
        # GH#54257
        ser = Series(range(3))

        msg = "No axis named 2 for object type Series"
        with pytest.raises(ValueError, match=msg):
            ser.argsort(axis=2)

    def test_argsort_numpy(self, datetime_series):
        ser = datetime_series

        res = np.argsort(ser).values
        expected = np.argsort(np.array(ser))
        tm.assert_numpy_array_equal(res, expected)

        # with missing values
        ts = ser.copy()
        ts[::2] = np.NaN

        msg = "The behavior of Series.argsort in the presence of NA values"
        with tm.assert_produces_warning(
            FutureWarning, match=msg, check_stacklevel=False
        ):
            result = np.argsort(ts)[1::2]
        expected = np.argsort(np.array(ts.dropna()))

        tm.assert_numpy_array_equal(result.values, expected)

    def test_argsort(self, datetime_series):
        argsorted = datetime_series.argsort()
        assert issubclass(argsorted.dtype.type, np.integer)

        # GH#2967 (introduced bug in 0.11-dev I think)
        s = Series([Timestamp(f"201301{i:02d}") for i in range(1, 6)])
        assert s.dtype == "datetime64[ns]"
        shifted = s.shift(-1)
        assert shifted.dtype == "datetime64[ns]"
        assert isna(shifted[4])

        result = s.argsort()
        expected = Series(range(5), dtype=np.intp)
        tm.assert_series_equal(result, expected)

        msg = "The behavior of Series.argsort in the presence of NA values"
        with tm.assert_produces_warning(FutureWarning, match=msg):
            result = shifted.argsort()
        expected = Series(list(range(4)) + [-1], dtype=np.intp)
        tm.assert_series_equal(result, expected)

    def test_argsort_stable(self):
        s = Series(np.random.randint(0, 100, size=10000))
        mindexer = s.argsort(kind="mergesort")
        qindexer = s.argsort()

        mexpected = np.argsort(s.values, kind="mergesort")
        qexpected = np.argsort(s.values, kind="quicksort")

        tm.assert_series_equal(mindexer.astype(np.intp), Series(mexpected))
        tm.assert_series_equal(qindexer.astype(np.intp), Series(qexpected))
        msg = (
            r"ndarray Expected type <class 'numpy\.ndarray'>, "
            r"found <class 'pandas\.core\.series\.Series'> instead"
        )
        with pytest.raises(AssertionError, match=msg):
            tm.assert_numpy_array_equal(qindexer, mindexer)

    def test_argsort_preserve_name(self, datetime_series):
        result = datetime_series.argsort()
        assert result.name == datetime_series.name
