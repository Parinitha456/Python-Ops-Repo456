import numpy as np
import pytest

import pandas.util._test_decorators as td

import pandas as pd
import pandas._testing as tm
from pandas.core.arrays import FloatingArray
from pandas.core.arrays.floating import Float32Dtype, Float64Dtype


def test_uses_pandas_na():
    a = pd.array([1, None], dtype=pd.Float64Dtype())
    assert a[1] is pd.NA


def test_floating_array_constructor():
    values = np.array([1, 2, 3, 4], dtype="float64")
    mask = np.array([False, False, False, True], dtype="bool")

    result = FloatingArray(values, mask)
    expected = pd.array([1, 2, 3, np.nan], dtype="Float64")
    tm.assert_extension_array_equal(result, expected)
    tm.assert_numpy_array_equal(result._data, values)
    tm.assert_numpy_array_equal(result._mask, mask)

    msg = r".* should be .* numpy array. Use the 'pd.array' function instead"
    with pytest.raises(TypeError, match=msg):
        FloatingArray(values.tolist(), mask)

    with pytest.raises(TypeError, match=msg):
        FloatingArray(values, mask.tolist())

    with pytest.raises(TypeError, match=msg):
        FloatingArray(values.astype(int), mask)

    msg = r"__init__\(\) missing 1 required positional argument: 'mask'"
    with pytest.raises(TypeError, match=msg):
        FloatingArray(values)


def test_floating_array_constructor_copy():
    values = np.array([1, 2, 3, 4], dtype="float64")
    mask = np.array([False, False, False, True], dtype="bool")

    result = FloatingArray(values, mask)
    assert result._data is values
    assert result._mask is mask

    result = FloatingArray(values, mask, copy=True)
    assert result._data is not values
    assert result._mask is not mask


def test_to_array():
    result = pd.array([0.1, 0.2, 0.3, 0.4])
    expected = pd.array([0.1, 0.2, 0.3, 0.4], dtype="Float64")
    tm.assert_extension_array_equal(result, expected)


@pytest.mark.parametrize(
    "a, b",
    [
        ([1, None], [1, pd.NA]),
        ([None], [pd.NA]),
        ([None, np.nan], [pd.NA, pd.NA]),
        ([1, np.nan], [1, pd.NA]),
        ([np.nan], [pd.NA]),
    ],
)
def test_to_array_none_is_nan(a, b):
    result = pd.array(a, dtype="Float64")
    expected = pd.array(b, dtype="Float64")
    tm.assert_extension_array_equal(result, expected)


@pytest.mark.parametrize(
    "values",
    [
        ["foo", "bar"],
        ["1", "2"],
        "foo",
        1,
        1.0,
        pd.date_range("20130101", periods=2),
        np.array(["foo"]),
        [[1, 2], [3, 4]],
        [np.nan, {"a": 1}],
    ],
)
def test_to_array_error(values):
    # error in converting existing arrays to FloatingArray
    msg = (
        r"(:?.* cannot be converted to a FloatingDtype)"
        r"|(:?values must be a 1D list-like)"
        r"|(:?Cannot pass scalar)"
    )
    with pytest.raises((TypeError, ValueError), match=msg):
        pd.array(values, dtype="Float64")


def test_to_array_inferred_dtype():
    # if values has dtype -> respect it
    result = pd.array(np.array([1, 2], dtype="float32"))
    assert result.dtype == Float32Dtype()

    # if values have no dtype -> always float64
    result = pd.array([1.0, 2.0])
    assert result.dtype == Float64Dtype()


def test_to_array_dtype_keyword():
    result = pd.array([1, 2], dtype="Float32")
    assert result.dtype == Float32Dtype()

    # if values has dtype -> override it
    result = pd.array(np.array([1, 2], dtype="float32"), dtype="Float64")
    assert result.dtype == Float64Dtype()


def test_to_array_integer():
    result = pd.array([1, 2], dtype="Float64")
    expected = pd.array([1.0, 2.0], dtype="Float64")
    tm.assert_extension_array_equal(result, expected)

    # for integer dtypes, the itemsize is not preserved
    # TODO can we specify "floating" in general?
    result = pd.array(np.array([1, 2], dtype="int32"), dtype="Float64")
    assert result.dtype == Float64Dtype()


@pytest.mark.parametrize(
    "bool_values, values, target_dtype, expected_dtype",
    [
        ([False, True], [0, 1], Float64Dtype(), Float64Dtype()),
        ([False, True], [0, 1], "Float64", Float64Dtype()),
        ([False, True, np.nan], [0, 1, np.nan], Float64Dtype(), Float64Dtype()),
    ],
)
def test_to_array_bool(bool_values, values, target_dtype, expected_dtype):
    result = pd.array(bool_values, dtype=target_dtype)
    assert result.dtype == expected_dtype
    expected = pd.array(values, dtype=target_dtype)
    tm.assert_extension_array_equal(result, expected)


def test_series_from_float(data):
    # construct from our dtype & string dtype
    dtype = data.dtype

    # from float
    expected = pd.Series(data)
    result = pd.Series(data.to_numpy(na_value=np.nan, dtype="float"), dtype=str(dtype))
    tm.assert_series_equal(result, expected)

    # from list
    expected = pd.Series(data)
    result = pd.Series(np.array(data).tolist(), dtype=str(dtype))
    tm.assert_series_equal(result, expected)


# TODO belongs in different file

# def test_conversions(data_missing):

#     # astype to object series
#     df = pd.DataFrame({"A": data_missing})
#     result = df["A"].astype("object")
#     expected = pd.Series(np.array([np.nan, 1], dtype=object), name="A")
#     tm.assert_series_equal(result, expected)

#     # convert to object ndarray
#     # we assert that we are exactly equal
#     # including type conversions of scalars
#     result = df["A"].astype("object").values
#     expected = np.array([pd.NA, 1], dtype=object)
#     tm.assert_numpy_array_equal(result, expected)

#     for r, e in zip(result, expected):
#         if pd.isnull(r):
#             assert pd.isnull(e)
#         elif is_integer(r):
#             assert r == e
#             assert is_integer(e)
#         else:
#             assert r == e
#             assert type(r) == type(e)


@td.skip_if_no("pyarrow", min_version="0.15.0")
def test_arrow_array(data):
    # protocol added in 0.15.0
    import pyarrow as pa

    arr = pa.array(data)
    expected = np.array(data, dtype=object)
    expected[data.isna()] = None
    expected = pa.array(expected, type=data.dtype.name.lower(), from_pandas=True)
    assert arr.equals(expected)


@td.skip_if_no("pyarrow", min_version="0.16.0")
def test_arrow_roundtrip(data):
    # roundtrip possible from arrow 0.16.0
    import pyarrow as pa

    df = pd.DataFrame({"a": data})
    table = pa.table(df)
    assert table.field("a").type == str(data.dtype.numpy_dtype)
    result = table.to_pandas()
    tm.assert_frame_equal(result, df)
