import numpy as np
import pytest

from pandas.errors import NumbaUtilError
import pandas.util._test_decorators as td

from pandas import DataFrame, NamedAgg, option_context
import pandas._testing as tm
from pandas.core.util.numba_ import NUMBA_FUNC_CACHE


@td.skip_if_no("numba", "0.46.0")
def test_correct_function_signature():
    def incorrect_function(x):
        return sum(x) * 2.7

    data = DataFrame(
        {"key": ["a", "a", "b", "b", "a"], "data": [1.0, 2.0, 3.0, 4.0, 5.0]},
        columns=["key", "data"],
    )
    with pytest.raises(NumbaUtilError, match="The first 2"):
        data.groupby("key").agg(incorrect_function, engine="numba")

    with pytest.raises(NumbaUtilError, match="The first 2"):
        data.groupby("key")["data"].agg(incorrect_function, engine="numba")


@td.skip_if_no("numba", "0.46.0")
def test_check_nopython_kwargs():
    def incorrect_function(x, **kwargs):
        return sum(x) * 2.7

    data = DataFrame(
        {"key": ["a", "a", "b", "b", "a"], "data": [1.0, 2.0, 3.0, 4.0, 5.0]},
        columns=["key", "data"],
    )
    with pytest.raises(NumbaUtilError, match="numba does not support"):
        data.groupby("key").agg(incorrect_function, engine="numba", a=1)

    with pytest.raises(NumbaUtilError, match="numba does not support"):
        data.groupby("key")["data"].agg(incorrect_function, engine="numba", a=1)


@td.skip_if_no("numba", "0.46.0")
@pytest.mark.filterwarnings("ignore:\\nThe keyword argument")
# Filter warnings when parallel=True and the function can't be parallelized by Numba
@pytest.mark.parametrize("jit", [True, False])
@pytest.mark.parametrize("pandas_obj", ["Series", "DataFrame"])
def test_numba_vs_cython(jit, pandas_obj, nogil, parallel, nopython):
    def func_numba(values, index):
        return np.mean(values) * 2.7

    if jit:
        # Test accepted jitted functions
        import numba

        func_numba = numba.jit(func_numba)

    data = DataFrame(
<<<<<<< HEAD
        {0: ["a", "a", "b", "b", "a"], 1: [1.0, 2.0, 3.0, 4.0, 5.0]}, columns=[0, 1]
=======
        {0: ["a", "a", "b", "b", "a"], 1: [1.0, 2.0, 3.0, 4.0, 5.0]},
        columns=[0, 1],
>>>>>>> c34ed0ebf1599a6ea21cf94846e4c7a8bb72a298
    )
    engine_kwargs = {"nogil": nogil, "parallel": parallel, "nopython": nopython}
    grouped = data.groupby(0)
    if pandas_obj == "Series":
        grouped = grouped[1]

    result = grouped.agg(func_numba, engine="numba", engine_kwargs=engine_kwargs)
    expected = grouped.agg(lambda x: np.mean(x) * 2.7, engine="cython")

    tm.assert_equal(result, expected)


@td.skip_if_no("numba", "0.46.0")
@pytest.mark.filterwarnings("ignore:\\nThe keyword argument")
# Filter warnings when parallel=True and the function can't be parallelized by Numba
@pytest.mark.parametrize("jit", [True, False])
@pytest.mark.parametrize("pandas_obj", ["Series", "DataFrame"])
def test_cache(jit, pandas_obj, nogil, parallel, nopython):
    # Test that the functions are cached correctly if we switch functions
    def func_1(values, index):
        return np.mean(values) - 3.4

    def func_2(values, index):
        return np.mean(values) * 2.7

    if jit:
        import numba

        func_1 = numba.jit(func_1)
        func_2 = numba.jit(func_2)

    data = DataFrame(
<<<<<<< HEAD
        {0: ["a", "a", "b", "b", "a"], 1: [1.0, 2.0, 3.0, 4.0, 5.0]}, columns=[0, 1]
=======
        {0: ["a", "a", "b", "b", "a"], 1: [1.0, 2.0, 3.0, 4.0, 5.0]},
        columns=[0, 1],
>>>>>>> c34ed0ebf1599a6ea21cf94846e4c7a8bb72a298
    )
    engine_kwargs = {"nogil": nogil, "parallel": parallel, "nopython": nopython}
    grouped = data.groupby(0)
    if pandas_obj == "Series":
        grouped = grouped[1]

    result = grouped.agg(func_1, engine="numba", engine_kwargs=engine_kwargs)
    expected = grouped.agg(lambda x: np.mean(x) - 3.4, engine="cython")
    tm.assert_equal(result, expected)
    # func_1 should be in the cache now
    assert (func_1, "groupby_agg") in NUMBA_FUNC_CACHE

    # Add func_2 to the cache
    result = grouped.agg(func_2, engine="numba", engine_kwargs=engine_kwargs)
    expected = grouped.agg(lambda x: np.mean(x) * 2.7, engine="cython")
    tm.assert_equal(result, expected)
    assert (func_2, "groupby_agg") in NUMBA_FUNC_CACHE

    # Retest func_1 which should use the cache
    result = grouped.agg(func_1, engine="numba", engine_kwargs=engine_kwargs)
    expected = grouped.agg(lambda x: np.mean(x) - 3.4, engine="cython")
    tm.assert_equal(result, expected)


@td.skip_if_no("numba", "0.46.0")
def test_use_global_config():
    def func_1(values, index):
        return np.mean(values) - 3.4

    data = DataFrame(
<<<<<<< HEAD
        {0: ["a", "a", "b", "b", "a"], 1: [1.0, 2.0, 3.0, 4.0, 5.0]}, columns=[0, 1]
=======
        {0: ["a", "a", "b", "b", "a"], 1: [1.0, 2.0, 3.0, 4.0, 5.0]},
        columns=[0, 1],
>>>>>>> c34ed0ebf1599a6ea21cf94846e4c7a8bb72a298
    )
    grouped = data.groupby(0)
    expected = grouped.agg(func_1, engine="numba")
    with option_context("compute.use_numba", True):
        result = grouped.agg(func_1, engine=None)
    tm.assert_frame_equal(expected, result)


@td.skip_if_no("numba", "0.46.0")
@pytest.mark.parametrize(
    "agg_func",
    [
        ["min", "max"],
        "min",
        {"B": ["min", "max"], "C": "sum"},
        NamedAgg(column="B", aggfunc="min"),
    ],
)
def test_multifunc_notimplimented(agg_func):
    data = DataFrame(
<<<<<<< HEAD
        {0: ["a", "a", "b", "b", "a"], 1: [1.0, 2.0, 3.0, 4.0, 5.0]}, columns=[0, 1]
=======
        {0: ["a", "a", "b", "b", "a"], 1: [1.0, 2.0, 3.0, 4.0, 5.0]},
        columns=[0, 1],
>>>>>>> c34ed0ebf1599a6ea21cf94846e4c7a8bb72a298
    )
    grouped = data.groupby(0)
    with pytest.raises(NotImplementedError, match="Numba engine can"):
        grouped.agg(agg_func, engine="numba")

    with pytest.raises(NotImplementedError, match="Numba engine can"):
        grouped[1].agg(agg_func, engine="numba")
