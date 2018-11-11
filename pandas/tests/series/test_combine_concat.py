# coding=utf-8
# pylint: disable-msg=E1101,W0612

from datetime import datetime

import numpy as np
import pytest

import pandas as pd
from pandas import DataFrame, DatetimeIndex, Series, compat, date_range
import pandas.util.testing as tm
from pandas.util.testing import assert_frame_equal, assert_series_equal


class TestSeriesCombine():

    def test_append(self, datetime_series, string_series, object_series):
        appendedSeries = string_series.append(object_series)
        for idx, value in compat.iteritems(appendedSeries):
            if idx in string_series.index:
                assert value == string_series[idx]
            elif idx in object_series.index:
                assert value == object_series[idx]
            else:
                raise AssertionError("orphaned index!")

        pytest.raises(ValueError, datetime_series.append, datetime_series,
                      verify_integrity=True)

    def test_append_many(self, datetime_series):
        pieces = [datetime_series[:5], datetime_series[5:10],
                  datetime_series[10:]]

        result = pieces[0].append(pieces[1:])
        assert_series_equal(result, datetime_series)

    def test_append_duplicates(self):
        # GH 13677
        s1 = pd.Series([1, 2, 3])
        s2 = pd.Series([4, 5, 6])
        exp = pd.Series([1, 2, 3, 4, 5, 6], index=[0, 1, 2, 0, 1, 2])
        tm.assert_series_equal(s1.append(s2), exp)
        tm.assert_series_equal(pd.concat([s1, s2]), exp)

        # the result must have RangeIndex
        exp = pd.Series([1, 2, 3, 4, 5, 6])
        tm.assert_series_equal(s1.append(s2, ignore_index=True),
                               exp, check_index_type=True)
        tm.assert_series_equal(pd.concat([s1, s2], ignore_index=True),
                               exp, check_index_type=True)

        msg = 'Indexes have overlapping values:'
        with pytest.raises(ValueError, match=msg):
            s1.append(s2, verify_integrity=True)
        with pytest.raises(ValueError, match=msg):
            pd.concat([s1, s2], verify_integrity=True)

    def test_combine_scalar(self):
        # GH 21248
        # Note - combine() with another Series is tested elsewhere because
        # it is used when testing operators
        s = pd.Series([i * 10 for i in range(5)])
        result = s.combine(3, lambda x, y: x + y)
        expected = pd.Series([i * 10 + 3 for i in range(5)])
        tm.assert_series_equal(result, expected)

        result = s.combine(22, lambda x, y: min(x, y))
        expected = pd.Series([min(i * 10, 22) for i in range(5)])
        tm.assert_series_equal(result, expected)

    def test_combine_first(self):
        values = tm.makeIntIndex(20).values.astype(float)
        series = Series(values, index=tm.makeIntIndex(20))

        series_copy = series * 2
        series_copy[::2] = np.NaN

        # nothing used from the input
        combined = series.combine_first(series_copy)

        tm.assert_series_equal(combined, series)

        # Holes filled from input
        combined = series_copy.combine_first(series)
        assert np.isfinite(combined).all()

        tm.assert_series_equal(combined[::2], series[::2])
        tm.assert_series_equal(combined[1::2], series_copy[1::2])

        # mixed types
        index = tm.makeStringIndex(20)
        floats = Series(tm.randn(20), index=index)
        strings = Series(tm.makeStringIndex(10), index=index[::2])

        combined = strings.combine_first(floats)

        tm.assert_series_equal(strings, combined.loc[index[::2]])
        tm.assert_series_equal(floats[1::2].astype(object),
                               combined.loc[index[1::2]])

        # corner case
        s = Series([1., 2, 3], index=[0, 1, 2])
        result = s.combine_first(Series([], index=[]))
        assert_series_equal(s, result)

    def test_update(self):
        s = Series([1.5, np.nan, 3., 4., np.nan])
        s2 = Series([np.nan, 3.5, np.nan, 5.])
        s.update(s2)

        expected = Series([1.5, 3.5, 3., 5., np.nan])
        assert_series_equal(s, expected)

        # GH 3217
        df = DataFrame([{"a": 1}, {"a": 3, "b": 2}])
        df['c'] = np.nan

        df['c'].update(Series(['foo'], index=[0]))
        expected = DataFrame([[1, np.nan, 'foo'], [3, 2., np.nan]],
                             columns=['a', 'b', 'c'])
        assert_frame_equal(df, expected)

    def test_update_dtypes(self):
        s = Series([1., 2., False, True])

        other = Series([45])
        s.update(other)

        expected = Series([45., 2., False, True])
        assert_series_equal(s, expected)

        s = Series([10, 11, 12])
        other = Series([61, 63], index=[1, 3])
        s.update(other)

        expected = Series([10, 61, 12])
        assert_series_equal(s, expected)

        # we always try to keep original dtype, even if other has different one
        s.update(other.astype(float))
        assert_series_equal(s, expected)

        # if keeping the dtype is not possible, we allow upcasting
        s.update(other + 0.1)
        expected = Series([10., 61.1, 12.])
        assert_series_equal(s, expected)

    def test_update_nooverwrite(self):
        s = Series([0, 1, 2, np.nan, np.nan, 5, 6, np.nan])
        other = Series([1, 3, np.nan, 7, 9], index=[1, 3, 5, 7, 9])

        s.update(other, overwrite=False)

        expected = Series([0, 1, 2, 3, np.nan, 5, 6, 7])
        assert_series_equal(s, expected)

    def test_update_filtered(self):
        # for small values, np.arange defaults to int32,
        # but pandas default (e.g. for "expected" below) is int64
        s = Series(np.arange(8), dtype='int64')
        other = Series(np.arange(8), dtype='int64') + 10

        s.update(other, filter_func=lambda x: x % 2 == 1)

        expected = Series([0, 11, 2, 13, 4, 15, 6, 17])
        assert_series_equal(s, expected)

    def test_update_raise(self):
        s = Series([0, 1, 2, np.nan, np.nan, 5, 6, np.nan])
        other = Series([1, 3, np.nan, 7, 9], index=[1, 3, 5, 7, 9])

        with pytest.raises(ValueError, match="Data overlaps"):
            s.update(other, errors='raise')

    def test_concat_empty_series_dtypes_roundtrips(self):

        # round-tripping with self & like self
        dtypes = map(np.dtype, ['float64', 'int8', 'uint8', 'bool', 'm8[ns]',
                                'M8[ns]'])

        for dtype in dtypes:
            assert pd.concat([Series(dtype=dtype)]).dtype == dtype
            assert pd.concat([Series(dtype=dtype),
                              Series(dtype=dtype)]).dtype == dtype

        def int_result_type(dtype, dtype2):
            typs = {dtype.kind, dtype2.kind}
            if not len(typs - {'i', 'u', 'b'}) and (dtype.kind == 'i' or
                                                    dtype2.kind == 'i'):
                return 'i'
            elif not len(typs - {'u', 'b'}) and (dtype.kind == 'u' or
                                                 dtype2.kind == 'u'):
                return 'u'
            return None

        def float_result_type(dtype, dtype2):
            typs = {dtype.kind, dtype2.kind}
            if not len(typs - {'f', 'i', 'u'}) and (dtype.kind == 'f' or
                                                    dtype2.kind == 'f'):
                return 'f'
            return None

        def get_result_type(dtype, dtype2):
            result = float_result_type(dtype, dtype2)
            if result is not None:
                return result
            result = int_result_type(dtype, dtype2)
            if result is not None:
                return result
            return 'O'

        for dtype in dtypes:
            for dtype2 in dtypes:
                if dtype == dtype2:
                    continue

                expected = get_result_type(dtype, dtype2)
                result = pd.concat([Series(dtype=dtype), Series(dtype=dtype2)
                                    ]).dtype
                assert result.kind == expected

    def test_combine_first_dt_tz_values(self, tz_naive_fixture):
        ser1 = pd.Series(pd.DatetimeIndex(['20150101', '20150102', '20150103'],
                                          tz=tz_naive_fixture),
                         name='ser1')
        ser2 = pd.Series(pd.DatetimeIndex(['20160514', '20160515', '20160516'],
                                          tz=tz_naive_fixture),
                         index=[2, 3, 4], name='ser2')
        result = ser1.combine_first(ser2)
        exp_vals = pd.DatetimeIndex(['20150101', '20150102', '20150103',
                                     '20160515', '20160516'],
                                    tz=tz_naive_fixture)
        exp = pd.Series(exp_vals, name='ser1')
        assert_series_equal(exp, result)

    def test_concat_empty_series_dtypes(self):

        # booleans
        assert pd.concat([Series(dtype=np.bool_),
                          Series(dtype=np.int32)]).dtype == np.int32
        assert pd.concat([Series(dtype=np.bool_),
                          Series(dtype=np.float32)]).dtype == np.object_

        # datetime-like
        assert pd.concat([Series(dtype='m8[ns]'),
                          Series(dtype=np.bool)]).dtype == np.object_
        assert pd.concat([Series(dtype='m8[ns]'),
                          Series(dtype=np.int64)]).dtype == np.object_
        assert pd.concat([Series(dtype='M8[ns]'),
                          Series(dtype=np.bool)]).dtype == np.object_
        assert pd.concat([Series(dtype='M8[ns]'),
                          Series(dtype=np.int64)]).dtype == np.object_
        assert pd.concat([Series(dtype='M8[ns]'),
                          Series(dtype=np.bool_),
                          Series(dtype=np.int64)]).dtype == np.object_

        # categorical
        assert pd.concat([Series(dtype='category'),
                          Series(dtype='category')]).dtype == 'category'
        # GH 18515
        assert pd.concat([Series(np.array([]), dtype='category'),
                          Series(dtype='float64')]).dtype == 'float64'
        assert pd.concat([Series(dtype='category'),
                          Series(dtype='object')]).dtype == 'object'

        # sparse
        # TODO: move?
        result = pd.concat([Series(dtype='float64').to_sparse(), Series(
            dtype='float64').to_sparse()])
        assert result.dtype == 'Sparse[float64]'
        assert result.ftype == 'float64:sparse'

        result = pd.concat([Series(dtype='float64').to_sparse(), Series(
            dtype='float64')])
        # TODO: release-note: concat sparse dtype
        expected = pd.core.sparse.api.SparseDtype(np.float64)
        assert result.dtype == expected
        assert result.ftype == 'float64:sparse'

        result = pd.concat([Series(dtype='float64').to_sparse(), Series(
            dtype='object')])
        # TODO: release-note: concat sparse dtype
        expected = pd.core.sparse.api.SparseDtype('object')
        assert result.dtype == expected
        assert result.ftype == 'object:sparse'

    def test_combine_first_dt64(self):
        from pandas.core.tools.datetimes import to_datetime
        s0 = to_datetime(Series(["2010", np.NaN]))
        s1 = to_datetime(Series([np.NaN, "2011"]))
        rs = s0.combine_first(s1)
        xp = to_datetime(Series(['2010', '2011']))
        assert_series_equal(rs, xp)

        s0 = to_datetime(Series(["2010", np.NaN]))
        s1 = Series([np.NaN, "2011"])
        rs = s0.combine_first(s1)
        xp = Series([datetime(2010, 1, 1), '2011'])
        assert_series_equal(rs, xp)


class TestTimeseries(object):

    def test_append_concat(self):
        rng = date_range('5/8/2012 1:45', periods=10, freq='5T')
        ts = Series(np.random.randn(len(rng)), rng)
        df = DataFrame(np.random.randn(len(rng), 4), index=rng)

        result = ts.append(ts)
        result_df = df.append(df)
        ex_index = DatetimeIndex(np.tile(rng.values, 2))
        tm.assert_index_equal(result.index, ex_index)
        tm.assert_index_equal(result_df.index, ex_index)

        appended = rng.append(rng)
        tm.assert_index_equal(appended, ex_index)

        appended = rng.append([rng, rng])
        ex_index = DatetimeIndex(np.tile(rng.values, 3))
        tm.assert_index_equal(appended, ex_index)

        # different index names
        rng1 = rng.copy()
        rng2 = rng.copy()
        rng1.name = 'foo'
        rng2.name = 'bar'
        assert rng1.append(rng1).name == 'foo'
        assert rng1.append(rng2).name is None

    def test_append_concat_tz(self):
        # see gh-2938
        rng = date_range('5/8/2012 1:45', periods=10, freq='5T',
                         tz='US/Eastern')
        rng2 = date_range('5/8/2012 2:35', periods=10, freq='5T',
                          tz='US/Eastern')
        rng3 = date_range('5/8/2012 1:45', periods=20, freq='5T',
                          tz='US/Eastern')
        ts = Series(np.random.randn(len(rng)), rng)
        df = DataFrame(np.random.randn(len(rng), 4), index=rng)
        ts2 = Series(np.random.randn(len(rng2)), rng2)
        df2 = DataFrame(np.random.randn(len(rng2), 4), index=rng2)

        result = ts.append(ts2)
        result_df = df.append(df2)
        tm.assert_index_equal(result.index, rng3)
        tm.assert_index_equal(result_df.index, rng3)

        appended = rng.append(rng2)
        tm.assert_index_equal(appended, rng3)

    def test_append_concat_tz_explicit_pytz(self):
        # see gh-2938
        from pytz import timezone as timezone

        rng = date_range('5/8/2012 1:45', periods=10, freq='5T',
                         tz=timezone('US/Eastern'))
        rng2 = date_range('5/8/2012 2:35', periods=10, freq='5T',
                          tz=timezone('US/Eastern'))
        rng3 = date_range('5/8/2012 1:45', periods=20, freq='5T',
                          tz=timezone('US/Eastern'))
        ts = Series(np.random.randn(len(rng)), rng)
        df = DataFrame(np.random.randn(len(rng), 4), index=rng)
        ts2 = Series(np.random.randn(len(rng2)), rng2)
        df2 = DataFrame(np.random.randn(len(rng2), 4), index=rng2)

        result = ts.append(ts2)
        result_df = df.append(df2)
        tm.assert_index_equal(result.index, rng3)
        tm.assert_index_equal(result_df.index, rng3)

        appended = rng.append(rng2)
        tm.assert_index_equal(appended, rng3)

    def test_append_concat_tz_dateutil(self):
        # see gh-2938
        rng = date_range('5/8/2012 1:45', periods=10, freq='5T',
                         tz='dateutil/US/Eastern')
        rng2 = date_range('5/8/2012 2:35', periods=10, freq='5T',
                          tz='dateutil/US/Eastern')
        rng3 = date_range('5/8/2012 1:45', periods=20, freq='5T',
                          tz='dateutil/US/Eastern')
        ts = Series(np.random.randn(len(rng)), rng)
        df = DataFrame(np.random.randn(len(rng), 4), index=rng)
        ts2 = Series(np.random.randn(len(rng2)), rng2)
        df2 = DataFrame(np.random.randn(len(rng2), 4), index=rng2)

        result = ts.append(ts2)
        result_df = df.append(df2)
        tm.assert_index_equal(result.index, rng3)
        tm.assert_index_equal(result_df.index, rng3)

        appended = rng.append(rng2)
        tm.assert_index_equal(appended, rng3)
