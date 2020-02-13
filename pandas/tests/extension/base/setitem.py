import operator

import numpy as np
import pytest

import pandas as pd
from pandas.core.arrays.numpy_ import PandasDtype

from .base import BaseExtensionTests


class BaseSetitemTests(BaseExtensionTests):
    def test_setitem_scalar_series(self, data, box_in_series):
        if box_in_series:
            data = pd.Series(data)
        data[0] = data[1]
        assert data[0] == data[1]

    def test_setitem_sequence(self, data, box_in_series):
        if box_in_series:
            data = pd.Series(data)
        original = data.copy()

        data[[0, 1]] = [data[1], data[0]]
        assert data[0] == original[1]
        assert data[1] == original[0]

    def test_setitem_sequence_mismatched_length_raises(self, data, as_array):
        ser = pd.Series(data)
        original = ser.copy()
        value = [data[0]]
        if as_array:
            value = data._from_sequence(value)

        xpr = "cannot set using a {} indexer with a different length"
        with pytest.raises(ValueError, match=xpr.format("list-like")):
            ser[[0, 1]] = value
        # Ensure no modifications made before the exception
        self.assert_series_equal(ser, original)

        with pytest.raises(ValueError, match=xpr.format("slice")):
            ser[slice(3)] = value
        self.assert_series_equal(ser, original)

    def test_setitem_empty_indxer(self, data, box_in_series):
        if box_in_series:
            data = pd.Series(data)
        original = data.copy()
        data[np.array([], dtype=int)] = []
        self.assert_equal(data, original)

    def test_setitem_sequence_broadcasts(self, data, box_in_series):
        if box_in_series:
            data = pd.Series(data)
        data[[0, 1]] = data[2]
        assert data[0] == data[2]
        assert data[1] == data[2]

    @pytest.mark.parametrize("setter", ["loc", "iloc"])
    def test_setitem_scalar(self, data, setter):
        arr = pd.Series(data)
        setter = getattr(arr, setter)
        operator.setitem(setter, 0, data[1])
        assert arr[0] == data[1]

    def test_setitem_loc_scalar_mixed(self, data):
        df = pd.DataFrame({"A": np.arange(len(data)), "B": data})
        df.loc[0, "B"] = data[1]
        assert df.loc[0, "B"] == data[1]

    def test_setitem_loc_scalar_single(self, data):
        df = pd.DataFrame({"B": data})
        df.loc[10, "B"] = data[1]
        assert df.loc[10, "B"] == data[1]

    def test_setitem_loc_scalar_multiple_homogoneous(self, data):
        df = pd.DataFrame({"A": data, "B": data})
        df.loc[10, "B"] = data[1]
        assert df.loc[10, "B"] == data[1]

    def test_setitem_iloc_scalar_mixed(self, data):
        df = pd.DataFrame({"A": np.arange(len(data)), "B": data})
        df.iloc[0, 1] = data[1]
        assert df.loc[0, "B"] == data[1]

    def test_setitem_iloc_scalar_single(self, data):
        df = pd.DataFrame({"B": data})
        df.iloc[10, 0] = data[1]
        assert df.loc[10, "B"] == data[1]

    def test_setitem_iloc_scalar_multiple_homogoneous(self, data):
        df = pd.DataFrame({"A": data, "B": data})
        df.iloc[10, 1] = data[1]
        assert df.loc[10, "B"] == data[1]

    @pytest.mark.parametrize("as_callable", [True, False])
    @pytest.mark.parametrize("setter", ["loc", None])
    def test_setitem_mask_aligned(self, data, as_callable, setter):
        ser = pd.Series(data)
        mask = np.zeros(len(data), dtype=bool)
        mask[:2] = True

        if as_callable:
            mask2 = lambda x: mask
        else:
            mask2 = mask

        if setter:
            # loc
            target = getattr(ser, setter)
        else:
            # Series.__setitem__
            target = ser

        operator.setitem(target, mask2, data[5:7])

        ser[mask2] = data[5:7]
        assert ser[0] == data[5]
        assert ser[1] == data[6]

    @pytest.mark.parametrize("setter", ["loc", None])
    def test_setitem_mask_broadcast(self, data, setter):
        ser = pd.Series(data)
        mask = np.zeros(len(data), dtype=bool)
        mask[:2] = True

        if setter:  # loc
            target = getattr(ser, setter)
        else:  # __setitem__
            target = ser

        operator.setitem(target, mask, data[10])
        assert ser[0] == data[10]
        assert ser[1] == data[10]

    def test_setitem_boolean_na_mask(self, data, box_in_series):
        # https://github.com/pandas-dev/pandas/issues/31503
        if box_in_series:
            data = pd.Series(data)

        mask = pd.array(np.zeros(len(data), dtype=bool), dtype="boolean")
        mask[:2] = pd.NA
        mask[2:4] = True
        original = data.copy()

        data[mask] = data[mask.fillna(False)]

        if box_in_series:
            tm.assert_series_equal(data, original)
        else:
            tm.assert_extension_array_equal(data, original)

    def test_setitem_boolean_na_mask_frame(self, data):
        # https://github.com/pandas-dev/pandas/issues/31503
        df = pd.DataFrame({"a": range(len(data)), "b": data})
        original = df.copy()

        mask = pd.array(np.zeros(len(data), dtype=bool), dtype="boolean")
        mask[:2] = pd.NA
        mask[2:4] = True

        df.loc[mask, "b"] = data[mask.fillna(False)]

        tm.assert_frame_equal(df, original)

    def test_setitem_expand_columns(self, data):
        df = pd.DataFrame({"A": data})
        result = df.copy()
        result["B"] = 1
        expected = pd.DataFrame({"A": data, "B": [1] * len(data)})
        self.assert_frame_equal(result, expected)

        result = df.copy()
        result.loc[:, "B"] = 1
        self.assert_frame_equal(result, expected)

        # overwrite with new type
        result["B"] = data
        expected = pd.DataFrame({"A": data, "B": data})
        self.assert_frame_equal(result, expected)

    def test_setitem_expand_with_extension(self, data):
        df = pd.DataFrame({"A": [1] * len(data)})
        result = df.copy()
        result["B"] = data
        expected = pd.DataFrame({"A": [1] * len(data), "B": data})
        self.assert_frame_equal(result, expected)

        result = df.copy()
        result.loc[:, "B"] = data
        self.assert_frame_equal(result, expected)

    def test_setitem_frame_invalid_length(self, data):
        df = pd.DataFrame({"A": [1] * len(data)})
        xpr = "Length of values does not match length of index"
        with pytest.raises(ValueError, match=xpr):
            df["B"] = data[:5]

    @pytest.mark.xfail(reason="GH#20441: setitem on extension types.")
    def test_setitem_tuple_index(self, data):
        s = pd.Series(data[:2], index=[(0, 0), (0, 1)])
        expected = pd.Series(data.take([1, 1]), index=s.index)
        s[(0, 1)] = data[1]
        self.assert_series_equal(s, expected)

    def test_setitem_slice(self, data, box_in_series):
        arr = data[:5].copy()
        expected = data.take([0, 0, 0, 3, 4])
        if box_in_series:
            arr = pd.Series(arr)
            expected = pd.Series(expected)

        arr[:3] = data[0]
        self.assert_equal(arr, expected)

    def test_setitem_loc_iloc_slice(self, data):
        arr = data[:5].copy()
        s = pd.Series(arr, index=["a", "b", "c", "d", "e"])
        expected = pd.Series(data.take([0, 0, 0, 3, 4]), index=s.index)

        result = s.copy()
        result.iloc[:3] = data[0]
        self.assert_equal(result, expected)

        result = s.copy()
        result.loc[:"c"] = data[0]
        self.assert_equal(result, expected)

    def test_setitem_slice_mismatch_length_raises(self, data):
        arr = data[:5]
        with pytest.raises(ValueError):
            arr[:1] = arr[:2]

    def test_setitem_slice_array(self, data):
        arr = data[:5].copy()
        arr[:5] = data[-5:]
        self.assert_extension_array_equal(arr, data[-5:])

    def test_setitem_scalar_key_sequence_raise(self, data):
        arr = data[:5].copy()
        with pytest.raises(ValueError):
            arr[0] = arr[[0, 1]]

    def test_setitem_preserves_views(self, data):
        # GH#28150 setitem shouldn't swap the underlying data
        view1 = data.view()
        view2 = data[:]

        data[0] = data[1]
        assert view1[0] == data[1]
        assert view2[0] == data[1]

    def test_setitem_nullable_mask(self, data):
        # GH 31446
        # TODO: there is some issue with PandasArray, therefore,
        # TODO: skip the setitem test for now, and fix it later
        if data.dtype != PandasDtype("object"):
            arr = data[:5]
            expected = data.take([0, 0, 0, 3, 4])
            mask = pd.array([True, True, True, False, False])
            arr[mask] = data[0]
            self.assert_extension_array_equal(expected, arr)
