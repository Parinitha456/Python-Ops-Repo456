"""
masked_reductions.py is for reduction algorithms using a mask-based approach
for missing values.
"""

from typing import Callable

import numpy as np

from pandas._libs import missing as libmissing
from pandas.compat.numpy import _np_version_under1p17

from pandas.core.nanops import check_below_min_count


def _sumprod(
    func: Callable,
    values: np.ndarray,
    mask: np.ndarray,
    skipna: bool = True,
    min_count: int = 0,
):
    """
    Sum or product for 1D masked array.

    Parameters
    ----------
    func : np.sum or np.prod
    values : np.ndarray
        Numpy array with the values (can be of any dtype that support the
        operation).
    mask : np.ndarray
        Boolean numpy array (True values indicate missing values).
    skipna : bool, default True
        Whether to skip NA.
    min_count : int, default 0
        The required number of valid values to perform the operation. If fewer than
        ``min_count`` non-NA values are present the result will be NA.
    """
    if not skipna:
        if mask.any() or check_below_min_count(values.shape, None, min_count):
            return libmissing.NA
        else:
            return func(values)
    else:
        if check_below_min_count(values.shape, mask, min_count):
            return libmissing.NA

        if _np_version_under1p17:
            return func(values[~mask])
        else:
            return func(values, where=~mask)


def _minmax(func: Callable, values: np.ndarray, mask: np.ndarray, skipna: bool = True):
    """
    Reduction for 1D masked array.

    Parameters
    ----------
    func : np.min or np.max
    values : np.ndarray
        Numpy array with the values (can be of any dtype that support the
        operation).
    mask : np.ndarray
        Boolean numpy array (True values indicate missing values).
    skipna : bool, default True
        Whether to skip NA.
    """
    if not skipna:
        if mask.any() or not values.size:
            # min/max with empty array raise in numpy, pandas returns NA
            return libmissing.NA
        else:
            return func(values)
    else:
        if not mask.all():
            return func(values[~mask])
        else:
            # min/max with empty array raise in numpy, pandas returns NA
            return libmissing.NA


def min(values: np.ndarray, mask: np.ndarray, skipna: bool = True):
    return _minmax(np.min, values=values, mask=mask, skipna=skipna)


def max(values: np.ndarray, mask: np.ndarray, skipna: bool = True):
    return _minmax(np.max, values=values, mask=mask, skipna=skipna)


def sum(values: np.ndarray, mask: np.ndarray, skipna: bool = True, min_count: int = 0):
    return _sumprod(
        np.sum, values=values, mask=mask, skipna=skipna, min_count=min_count
    )


def prod(values: np.ndarray, mask: np.ndarray, skipna: bool = True, min_count: int = 0):
    return _sumprod(
        np.prod, values=values, mask=mask, skipna=skipna, min_count=min_count
    )
