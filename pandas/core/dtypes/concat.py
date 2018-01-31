"""
Utility functions related to concat
"""

import numpy as np
import pandas._libs.tslib as tslib
from pandas import compat
from pandas.core.dtypes.common import (
    is_categorical_dtype,
    is_sparse,
    is_datetimetz,
    is_datetime64_dtype,
    is_timedelta64_dtype,
    is_period_dtype,
    is_object_dtype,
    is_bool_dtype,
    is_dtype_equal,
    _NS_DTYPE,
    _TD_DTYPE)
from pandas.core.dtypes.generic import (
    ABCDatetimeIndex, ABCTimedeltaIndex,
    ABCPeriodIndex, ABCRangeIndex, ABCSparseDataFrame)


def get_dtype_kinds(l):
    """
    Parameters
    ----------
    l : list of arrays

    Returns
    -------
    a set of kinds that exist in this list of arrays
    """

    typs = set()
    for arr in l:

        dtype = arr.dtype
        if is_categorical_dtype(dtype):
            typ = 'category'
        elif is_sparse(arr):
            typ = 'sparse'
        elif isinstance(arr, ABCRangeIndex):
            typ = 'range'
        elif is_datetimetz(arr):
            # if to_concat contains different tz,
            # the result must be object dtype
            typ = str(arr.dtype)
        elif is_datetime64_dtype(dtype):
            typ = 'datetime'
        elif is_timedelta64_dtype(dtype):
            typ = 'timedelta'
        elif is_object_dtype(dtype):
            typ = 'object'
        elif is_bool_dtype(dtype):
            typ = 'bool'
        elif is_period_dtype(dtype):
            typ = str(arr.dtype)
        else:
            typ = dtype.kind
        typs.add(typ)
    return typs


def _get_series_result_type(result, objs=None):
    """
    return appropriate class of Series concat
    input is either dict or array-like
    """
    # concat Series with axis 1
    if isinstance(result, dict):
        # concat Series with axis 1
        if all(is_sparse(c) for c in compat.itervalues(result)):
            from pandas.core.sparse.api import SparseDataFrame
            return SparseDataFrame
        else:
            from pandas.core.frame import DataFrame
            return DataFrame

    # otherwise it is a SingleBlockManager (axis = 0)
    if result._block.is_sparse:
        from pandas.core.sparse.api import SparseSeries
        return SparseSeries
    else:
        return objs[0]._constructor


def _get_frame_result_type(result, objs):
    """
    return appropriate class of DataFrame-like concat
    if all blocks are SparseBlock, return SparseDataFrame
    otherwise, return 1st obj
    """

    from pandas.core.sparse.api import SparseDataFrame

    if result.blocks and all(b.is_sparse for b in result.blocks):
        return SparseDataFrame
    else:
        return next(obj for obj in objs if not isinstance(obj,
                                                          ABCSparseDataFrame))


def _concat_compat(to_concat, axis=0):
    """
    provide concatenation of an array of arrays each of which is a single
    'normalized' dtypes (in that for example, if it's object, then it is a
    non-datetimelike and provide a combined dtype for the resulting array that
    preserves the overall dtype if possible)

    Parameters
    ----------
    to_concat : array of arrays
    axis : axis to provide concatenation

    Returns
    -------
    a single array, preserving the combined dtypes
    """

    # filter empty arrays
    # 1-d dtypes always are included here
    def is_nonempty(x):
        try:
            return x.shape[axis] > 0
        except Exception:
            return True

    nonempty = [x for x in to_concat if is_nonempty(x)]

    # If all arrays are empty, there's nothing to convert, just short-cut to
    # the concatenation, #3121.
    #
    # Creating an empty array directly is tempting, but the winnings would be
    # marginal given that it would still require shape & dtype calculation and
    # np.concatenate which has them both implemented is compiled.

    typs = get_dtype_kinds(to_concat)

    _contains_datetime = any(typ.startswith('datetime') for typ in typs)
    _contains_period = any(typ.startswith('period') for typ in typs)

    if 'category' in typs:
        # this must be priort to _concat_datetime,
        # to support Categorical + datetime-like
        return _concat_categorical(to_concat, axis=axis)

    elif _contains_datetime or 'timedelta' in typs or _contains_period:
        return _concat_datetime(to_concat, axis=axis, typs=typs)

    # these are mandated to handle empties as well
    elif 'sparse' in typs:
        return _concat_sparse(to_concat, axis=axis, typs=typs)

    if not nonempty:
        # we have all empties, but may need to coerce the result dtype to
        # object if we have non-numeric type operands (numpy would otherwise
        # cast this to float)
        typs = get_dtype_kinds(to_concat)
        if len(typs) != 1:

            if (not len(typs - set(['i', 'u', 'f'])) or
                    not len(typs - set(['bool', 'i', 'u']))):
                # let numpy coerce
                pass
            else:
                # coerce to object
                to_concat = [x.astype('object') for x in to_concat]

    return np.concatenate(to_concat, axis=axis)


def _concat_categorical(to_concat, axis=0):
    """Concatenate an object/categorical array of arrays, each of which is a
    single dtype

    Parameters
    ----------
    to_concat : array of arrays
    axis : int
        Axis to provide concatenation in the current implementation this is
        always 0, e.g. we only have 1D categoricals

    Returns
    -------
    Categorical
        A single array, preserving the combined dtypes
    """

    def _concat_asobject(to_concat):
        to_concat = [x.get_values() if is_categorical_dtype(x.dtype)
                     else x.ravel() for x in to_concat]
        res = _concat_compat(to_concat)
        if axis == 1:
            return res.reshape(1, len(res))
        else:
            return res

    # we could have object blocks and categoricals here
    # if we only have a single categoricals then combine everything
    # else its a non-compat categorical
    categoricals = [x for x in to_concat if is_categorical_dtype(x.dtype)]

    # validate the categories
    if len(categoricals) != len(to_concat):
        pass
    else:
        # when all categories are identical
        first = to_concat[0]
        if all(first.is_dtype_equal(other) for other in to_concat[1:]):
            return union_categoricals(categoricals)

    return _concat_asobject(to_concat)


def union_categoricals(to_union, sort_categories=False, ignore_order=False):
    """
    Combine list-like of Categorical-like, unioning categories. All
    categories must have the same dtype.

    .. versionadded:: 0.19.0

    Parameters
    ----------
    to_union : list-like of Categorical, CategoricalIndex,
               or Series with dtype='category'
    sort_categories : boolean, default False
        If true, resulting categories will be lexsorted, otherwise
        they will be ordered as they appear in the data.
    ignore_order: boolean, default False
        If true, the ordered attribute of the Categoricals will be ignored.
        Results in an unordered categorical.

        .. versionadded:: 0.20.0

    Returns
    -------
    result : Categorical

    Raises
    ------
    TypeError
        - all inputs do not have the same dtype
        - all inputs do not have the same ordered property
        - all inputs are ordered and their categories are not identical
        - sort_categories=True and Categoricals are ordered
    ValueError
        Empty list of categoricals passed

    Notes
    -----

    To learn more about categories, see `link
    <http://pandas.pydata.org/pandas-docs/stable/categorical.html#unioning>`__

    Examples
    --------

    >>> from pandas.api.types import union_categoricals

    If you want to combine categoricals that do not necessarily have
    the same categories, `union_categoricals` will combine a list-like
    of categoricals. The new categories will be the union of the
    categories being combined.

    >>> a = pd.Categorical(["b", "c"])
    >>> b = pd.Categorical(["a", "b"])
    >>> union_categoricals([a, b])
    [b, c, a, b]
    Categories (3, object): [b, c, a]

    By default, the resulting categories will be ordered as they appear
    in the `categories` of the data. If you want the categories to be
    lexsorted, use `sort_categories=True` argument.

    >>> union_categoricals([a, b], sort_categories=True)
    [b, c, a, b]
    Categories (3, object): [a, b, c]

    `union_categoricals` also works with the case of combining two
    categoricals of the same categories and order information (e.g. what
    you could also `append` for).

    >>> a = pd.Categorical(["a", "b"], ordered=True)
    >>> b = pd.Categorical(["a", "b", "a"], ordered=True)
    >>> union_categoricals([a, b])
    [a, b, a, b, a]
    Categories (2, object): [a < b]

    Raises `TypeError` because the categories are ordered and not identical.

    >>> a = pd.Categorical(["a", "b"], ordered=True)
    >>> b = pd.Categorical(["a", "b", "c"], ordered=True)
    >>> union_categoricals([a, b])
    TypeError: to union ordered Categoricals, all categories must be the same

    New in version 0.20.0

    Ordered categoricals with different categories or orderings can be
    combined by using the `ignore_ordered=True` argument.

    >>> a = pd.Categorical(["a", "b", "c"], ordered=True)
    >>> b = pd.Categorical(["c", "b", "a"], ordered=True)
    >>> union_categoricals([a, b], ignore_order=True)
    [a, b, c, c, b, a]
    Categories (3, object): [a, b, c]

    `union_categoricals` also works with a `CategoricalIndex`, or `Series`
    containing categorical data, but note that the resulting array will
    always be a plain `Categorical`

    >>> a = pd.Series(["b", "c"], dtype='category')
    >>> b = pd.Series(["a", "b"], dtype='category')
    >>> union_categoricals([a, b])
    [b, c, a, b]
    Categories (3, object): [b, c, a]
    """
    from pandas import Index, Categorical, CategoricalIndex, Series
    from pandas.core.arrays.categorical import _recode_for_categories

    if len(to_union) == 0:
        raise ValueError('No Categoricals to union')

    def _maybe_unwrap(x):
        if isinstance(x, (CategoricalIndex, Series)):
            return x.values
        elif isinstance(x, Categorical):
            return x
        else:
            raise TypeError("all components to combine must be Categorical")

    to_union = [_maybe_unwrap(x) for x in to_union]
    first = to_union[0]

    if not all(is_dtype_equal(other.categories.dtype, first.categories.dtype)
               for other in to_union[1:]):
        raise TypeError("dtype of categories must be the same")

    ordered = False
    if all(first.is_dtype_equal(other) for other in to_union[1:]):
        # identical categories - fastpath
        categories = first.categories
        ordered = first.ordered

        if all(first.categories.equals(other.categories)
               for other in to_union[1:]):
            new_codes = np.concatenate([c.codes for c in to_union])
        else:
            codes = [first.codes] + [_recode_for_categories(other.codes,
                                                            other.categories,
                                                            first.categories)
                                     for other in to_union[1:]]
            new_codes = np.concatenate(codes)

        if sort_categories and not ignore_order and ordered:
            raise TypeError("Cannot use sort_categories=True with "
                            "ordered Categoricals")

        if sort_categories and not categories.is_monotonic_increasing:
            categories = categories.sort_values()
            indexer = categories.get_indexer(first.categories)

            from pandas.core.algorithms import take_1d
            new_codes = take_1d(indexer, new_codes, fill_value=-1)
    elif ignore_order or all(not c.ordered for c in to_union):
        # different categories - union and recode
        cats = first.categories.append([c.categories for c in to_union[1:]])
        categories = Index(cats.unique())
        if sort_categories:
            categories = categories.sort_values()

        new_codes = []
        for c in to_union:
            new_codes.append(_recode_for_categories(c.codes, c.categories,
                                                    categories))
        new_codes = np.concatenate(new_codes)
    else:
        # ordered - to show a proper error message
        if all(c.ordered for c in to_union):
            msg = ("to union ordered Categoricals, "
                   "all categories must be the same")
            raise TypeError(msg)
        else:
            raise TypeError('Categorical.ordered must be the same')

    if ignore_order:
        ordered = False

    return Categorical(new_codes, categories=categories, ordered=ordered,
                       fastpath=True)


def _concat_datetime(to_concat, axis=0, typs=None):
    """
    provide concatenation of an datetimelike array of arrays each of which is a
    single M8[ns], datetimet64[ns, tz] or m8[ns] dtype

    Parameters
    ----------
    to_concat : array of arrays
    axis : axis to provide concatenation
    typs : set of to_concat dtypes

    Returns
    -------
    a single array, preserving the combined dtypes
    """

    def convert_to_pydatetime(x, axis):
        # coerce to an object dtype

        # if dtype is of datetimetz or timezone
        if x.dtype.kind == _NS_DTYPE.kind:
            if getattr(x, 'tz', None) is not None:
                x = x.astype(object).values
            else:
                shape = x.shape
                x = tslib.ints_to_pydatetime(x.view(np.int64).ravel(),
                                             box="timestamp")
                x = x.reshape(shape)

        elif x.dtype == _TD_DTYPE:
            shape = x.shape
            x = tslib.ints_to_pytimedelta(x.view(np.int64).ravel(), box=True)
            x = x.reshape(shape)

        if axis == 1:
            x = np.atleast_2d(x)
        return x

    if typs is None:
        typs = get_dtype_kinds(to_concat)

    # must be single dtype
    if len(typs) == 1:
        _contains_datetime = any(typ.startswith('datetime') for typ in typs)
        _contains_period = any(typ.startswith('period') for typ in typs)

        if _contains_datetime:

            if 'datetime' in typs:
                new_values = np.concatenate([x.view(np.int64) for x in
                                             to_concat], axis=axis)
                return new_values.view(_NS_DTYPE)
            else:
                # when to_concat has different tz, len(typs) > 1.
                # thus no need to care
                return _concat_datetimetz(to_concat)

        elif 'timedelta' in typs:
            new_values = np.concatenate([x.view(np.int64) for x in to_concat],
                                        axis=axis)
            return new_values.view(_TD_DTYPE)

        elif _contains_period:
            # PeriodIndex must be handled by PeriodIndex,
            # Thus can't meet this condition ATM
            # Must be changed when we adding PeriodDtype
            raise NotImplementedError

    # need to coerce to object
    to_concat = [convert_to_pydatetime(x, axis) for x in to_concat]
    return np.concatenate(to_concat, axis=axis)


def _concat_datetimetz(to_concat, name=None):
    """
    concat DatetimeIndex with the same tz
    all inputs must be DatetimeIndex
    it is used in DatetimeIndex.append also
    """
    # do not pass tz to set because tzlocal cannot be hashed
    if len({str(x.dtype) for x in to_concat}) != 1:
        raise ValueError('to_concat must have the same tz')
    tz = to_concat[0].tz
    # no need to localize because internal repr will not be changed
    new_values = np.concatenate([x.asi8 for x in to_concat])
    return to_concat[0]._simple_new(new_values, tz=tz, name=name)


def _concat_index_same_dtype(indexes, klass=None):
    klass = klass if klass is not None else indexes[0].__class__
    return klass(np.concatenate([x._values for x in indexes]))


def _concat_index_asobject(to_concat, name=None):
    """
    concat all inputs as object. DatetimeIndex, TimedeltaIndex and
    PeriodIndex are converted to object dtype before concatenation
    """

    klasses = ABCDatetimeIndex, ABCTimedeltaIndex, ABCPeriodIndex
    to_concat = [x.astype(object) if isinstance(x, klasses) else x
                 for x in to_concat]

    from pandas import Index
    self = to_concat[0]
    attribs = self._get_attributes_dict()
    attribs['name'] = name

    to_concat = [x._values if isinstance(x, Index) else x
                 for x in to_concat]
    return self._shallow_copy_with_infer(np.concatenate(to_concat), **attribs)


def _concat_sparse(to_concat, axis=0, typs=None):
    """
    provide concatenation of an sparse/dense array of arrays each of which is a
    single dtype

    Parameters
    ----------
    to_concat : array of arrays
    axis : axis to provide concatenation
    typs : set of to_concat dtypes

    Returns
    -------
    a single array, preserving the combined dtypes
    """

    from pandas.core.sparse.array import SparseArray, _make_index

    def convert_sparse(x, axis):
        # coerce to native type
        if isinstance(x, SparseArray):
            x = x.get_values()
        x = x.ravel()
        if axis > 0:
            x = np.atleast_2d(x)
        return x

    if typs is None:
        typs = get_dtype_kinds(to_concat)

    if len(typs) == 1:
        # concat input as it is if all inputs are sparse
        # and have the same fill_value
        fill_values = {c.fill_value for c in to_concat}
        if len(fill_values) == 1:
            sp_values = [c.sp_values for c in to_concat]
            indexes = [c.sp_index.to_int_index() for c in to_concat]

            indices = []
            loc = 0
            for idx in indexes:
                indices.append(idx.indices + loc)
                loc += idx.length
            sp_values = np.concatenate(sp_values)
            indices = np.concatenate(indices)
            sp_index = _make_index(loc, indices, kind=to_concat[0].sp_index)

            return SparseArray(sp_values, sparse_index=sp_index,
                               fill_value=to_concat[0].fill_value)

    # input may be sparse / dense mixed and may have different fill_value
    # input must contain sparse at least 1
    sparses = [c for c in to_concat if is_sparse(c)]
    fill_values = [c.fill_value for c in sparses]
    sp_indexes = [c.sp_index for c in sparses]

    # densify and regular concat
    to_concat = [convert_sparse(x, axis) for x in to_concat]
    result = np.concatenate(to_concat, axis=axis)

    if not len(typs - set(['sparse', 'f', 'i'])):
        # sparsify if inputs are sparse and dense numerics
        # first sparse input's fill_value and SparseIndex is used
        result = SparseArray(result.ravel(), fill_value=fill_values[0],
                             kind=sp_indexes[0])
    else:
        # coerce to object if needed
        result = result.astype('object')
    return result


def _concat_rangeindex_same_dtype(indexes):
    """
    Concatenates multiple RangeIndex instances. All members of "indexes" must
    be of type RangeIndex; result will be RangeIndex if possible, Int64Index
    otherwise. E.g.:
    indexes = [RangeIndex(3), RangeIndex(3, 6)] -> RangeIndex(6)
    indexes = [RangeIndex(3), RangeIndex(4, 6)] -> Int64Index([0,1,2,4,5])
    """
    from pandas import Int64Index, RangeIndex

    start = step = next = None

    # Filter the empty indexes
    non_empty_indexes = [obj for obj in indexes if len(obj)]

    for obj in non_empty_indexes:

        if start is None:
            # This is set by the first non-empty index
            start = obj._start
            if step is None and len(obj) > 1:
                step = obj._step
        elif step is None:
            # First non-empty index had only one element
            if obj._start == start:
                return _concat_index_same_dtype(indexes, klass=Int64Index)
            step = obj._start - start

        non_consecutive = ((step != obj._step and len(obj) > 1) or
                           (next is not None and obj._start != next))
        if non_consecutive:
            return _concat_index_same_dtype(indexes, klass=Int64Index)

        if step is not None:
            next = obj[-1] + step

    if non_empty_indexes:
        # Get the stop value from "next" or alternatively
        # from the last non-empty index
        stop = non_empty_indexes[-1]._stop if next is None else next
        return RangeIndex(start, stop, step)

    # Here all "indexes" had 0 length, i.e. were empty.
    # In this case return an empty range index.
    return RangeIndex(0, 0)
