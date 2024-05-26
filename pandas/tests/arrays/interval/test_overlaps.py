"""Tests for Interval-Interval operations, such as overlaps, contains, etc."""

import numpy as np
import pytest

from pandas import (
    Interval,
    IntervalIndex,
    Timedelta,
    Timestamp,
)
import pandas._testing as tm
from pandas.core.arrays import IntervalArray


@pytest.fixture(params=[IntervalArray, IntervalIndex])
def constructor(request):
    """
    Fixture for testing both interval container classes.
    """
    return request.param


@pytest.fixture(
    params=[
        (Timedelta("0 days"), Timedelta("1 day")),
        (Timestamp("2018-01-01"), Timedelta("1 day")),
        (0, 1),
    ],
    ids=lambda x: type(x[0]).__name__,
)
def start_shift(request):
    """
    Fixture for generating intervals of different types from a start value
    and a shift value that can be added to start to generate an endpoint.
    """
    return request.param


class TestOverlaps:
    def test_overlaps_interval(self, constructor, start_shift, closed, other_closed):
        start, shift = start_shift
        interval = Interval(start, start + 3 * shift, other_closed)

        # intervals: identical, nested, spanning, partial, adjacent, disjoint
        tuples = [
            (start, start + 3 * shift),
            (start + shift, start + 2 * shift),
            (start - shift, start + 4 * shift),
            (start + 2 * shift, start + 4 * shift),
            (start + 3 * shift, start + 4 * shift),
            (start + 4 * shift, start + 5 * shift),
        ]
        interval_container = constructor.from_tuples(tuples, closed)

        adjacent = interval.closed_right and interval_container.closed_left
        expected = np.array([True, True, True, True, adjacent, False])
        result = interval_container.overlaps(interval)
        tm.assert_numpy_array_equal(result, expected)

    @pytest.mark.parametrize("other_constructor", [IntervalArray, IntervalIndex])
    def test_overlaps_interval_container(self, constructor, other_constructor):
        # TODO: modify this test when implemented
        interval_container = constructor.from_breaks(range(5))
        other_container = other_constructor.from_breaks(range(5))
        with pytest.raises(NotImplementedError, match="^$"):
            interval_container.overlaps(other_container)

    def test_overlaps_na(self, constructor, start_shift):
        """NA values are marked as False"""
        start, shift = start_shift
        interval = Interval(start, start + shift)

        tuples = [
            (start, start + shift),
            np.nan,
            (start + 2 * shift, start + 3 * shift),
        ]
        interval_container = constructor.from_tuples(tuples)

        expected = np.array([True, False, False])
        result = interval_container.overlaps(interval)
        tm.assert_numpy_array_equal(result, expected)

    @pytest.mark.parametrize(
        "other",
        [10, True, "foo", Timedelta("1 day"), Timestamp("2018-01-01")],
        ids=lambda x: type(x).__name__,
    )
    def test_overlaps_invalid_type(self, constructor, other):
        interval_container = constructor.from_breaks(range(5))
        msg = f"`other` must be Interval-like, got {type(other).__name__}"
        with pytest.raises(TypeError, match=msg):
            interval_container.overlaps(other)


class TestIntersection:
    def test_intersection_interval_array(self):
        interval = Interval(1, 8, "left")

        tuples = [  # Intervals:
            (1, 8),  # identical
            (2, 4),  # nested
            (0, 9),  # spanning
            (4, 10),  # partial
            (-5, 1),  # adjacent closed
            (8, 10),  # adjacent open
            (10, 15),  # disjoint
        ]
        interval_container = IntervalArray.from_tuples(tuples, "both")

        expected = np.array(
            [
                Interval(1, 8, "left"),
                Interval(2, 4, "both"),
                Interval(1, 8, "left"),
                Interval(4, 8, "left"),
                Interval(1, 1, "both"),
                None,
                None,
            ]
        )
        result = interval_container.intersection(interval)
        tm.assert_numpy_array_equal(result, expected)

    @pytest.mark.parametrize(
        "other",
        [10, True, "foo", Timedelta("1 day"), Timestamp("2018-01-01")],
        ids=lambda x: type(x).__name__,
    )
    def test_intersection_invalid_type(self, other):
        interval_container = IntervalArray.from_breaks(range(5))
        msg = f"`other` must be Interval-like, got {type(other).__name__}"
        with pytest.raises(TypeError, match=msg):
            interval_container.intersection(other)


class TestUnion:
    def test_union_interval_array(self):
        interval = Interval(1, 8, "left")

        tuples = [  # Intervals:
            (1, 8),  # identical
            (2, 4),  # nested
            (0, 9),  # spanning
            (4, 10),  # partial
            (-5, 1),  # adjacent closed
            (8, 10),  # adjacent open
            (10, 15),  # disjoint
        ]
        interval_container = IntervalArray.from_tuples(tuples, "both")

        expected = np.array(
            [
                np.array([Interval(1, 8, "both")], dtype=object),
                np.array([Interval(1, 8, "left")], dtype=object),
                np.array([Interval(0, 9, "both")], dtype=object),
                np.array([Interval(1, 10, "both")], dtype=object),
                np.array([Interval(-5, 8, "left")], dtype=object),
                np.array([Interval(1, 10, "both")], dtype=object),
                np.array(
                    [Interval(1, 8, "left"), Interval(10, 15, "both")], dtype=object
                ),
            ],
            dtype=object,
        )
        result = interval_container.union(interval)
        tm.assert_numpy_array_equal(result, expected)

    @pytest.mark.parametrize(
        "other",
        [10, True, "foo", Timedelta("1 day"), Timestamp("2018-01-01")],
        ids=lambda x: type(x).__name__,
    )
    def test_union_invalid_type(self, other):
        interval_container = IntervalArray.from_breaks(range(5))
        msg = f"`other` must be Interval-like, got {type(other).__name__}"
        with pytest.raises(TypeError, match=msg):
            interval_container.union(other)


class TestDifference:
    def test_difference_interval_array(self):
        interval = Interval(1, 8, "left")

        tuples = [  # Intervals:
            (1, 8),  # identical
            (2, 4),  # nested
            (0, 9),  # spanning
            (4, 10),  # partial
            (-5, 1),  # adjacent closed
            (8, 10),  # adjacent open
            (10, 15),  # disjoint
        ]
        interval_container = IntervalArray.from_tuples(tuples, "both")

        expected = np.array(
            [
                np.array([Interval(8, 8, "both")], dtype=object),
                np.array([], dtype=object),
                np.array(
                    [Interval(0, 1, "left"), Interval(8, 9, "both")], dtype=object
                ),
                np.array([Interval(8, 10, "both")], dtype=object),
                np.array([Interval(-5, 1, "left")], dtype=object),
                np.array([Interval(8, 10, "both")], dtype=object),
                np.array([Interval(10, 15, "both")], dtype=object),
            ],
            dtype=object,
        )
        result = interval_container.difference(interval)
        tm.assert_numpy_array_equal(result, expected)

    @pytest.mark.parametrize(
        "other",
        [10, True, "foo", Timedelta("1 day"), Timestamp("2018-01-01")],
        ids=lambda x: type(x).__name__,
    )
    def test_difference_invalid_type(self, other):
        interval_container = IntervalArray.from_breaks(range(5))
        msg = f"`other` must be Interval-like, got {type(other).__name__}"
        with pytest.raises(TypeError, match=msg):
            interval_container.difference(other)
