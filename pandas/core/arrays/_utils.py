from __future__ import annotations

import numpy as np

from pandas._libs import lib
from pandas.errors import LossySetitemError

from pandas.core.dtypes.cast import np_can_hold_element
from pandas.core.dtypes.common import is_numeric_dtype


def _to_numpy_dtype_inference(arr, dtype, na_value, hasna):
    if dtype is None and is_numeric_dtype(arr.dtype):
        dtype_given = False
        if hasna:
            if arr.dtype.kind == "b":
                dtype = object
            else:
                if arr.dtype.kind in "iu":
                    dtype = np.dtype(np.float64)
                else:
                    dtype = arr.dtype.numpy_dtype
                if na_value is lib.no_default:
                    na_value = np.nan
        else:
            dtype = arr.dtype.numpy_dtype
    elif dtype is not None:
        dtype = np.dtype(dtype)
        dtype_given = True
    else:
        dtype_given = True

    if na_value is lib.no_default:
        na_value = arr.dtype.na_value

    if not dtype_given and hasna:
        try:
            np_can_hold_element(dtype, na_value)
        except LossySetitemError:
            dtype = object
    return dtype, na_value
