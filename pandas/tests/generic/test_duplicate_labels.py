"""Tests dealing with the NDFrame.allows_duplicates."""
import operator

import numpy as np
import pytest

import pandas as pd
import pandas._testing as tm

not_implemented = pytest.mark.xfail(reason="Not implemented.")

# ----------------------------------------------------------------------------
# Preservation


class TestPreserves:
    @pytest.mark.parametrize(
        "cls, data",
        [
            (pd.Series, np.array([])),
            (pd.Series, [1, 2]),
            (pd.DataFrame, {}),
            (pd.DataFrame, {"A": [1, 2]}),
        ],
    )
    def test_construction_ok(self, cls, data):
        result = cls(data)
        assert result.allows_duplicate_labels is True

        result = cls(data, allows_duplicate_labels=False)
        assert result.allows_duplicate_labels is False

    @pytest.mark.parametrize(
        "func",
        [
            operator.itemgetter(["a"]),
            operator.methodcaller("add", 1),
            operator.methodcaller("rename", str.upper),
            operator.methodcaller("rename", "name"),
            pytest.param(operator.methodcaller("abs"), marks=not_implemented),
            # TODO: test np.abs
        ],
    )
    def test_preserved_series(self, func):
        s = pd.Series([0, 1], index=["a", "b"], allows_duplicate_labels=False)
        assert func(s).allows_duplicate_labels is False

    @pytest.mark.parametrize(
        "other", [pd.Series(0, index=["a", "b", "c"]), pd.Series(0, index=["a", "b"])]
    )
    # TODO: frame
    @not_implemented
    def test_align(self, other):
        s = pd.Series([0, 1], index=["a", "b"], allows_duplicate_labels=False)
        a, b = s.align(other)
        assert a.allows_duplicate_labels is False
        assert b.allows_duplicate_labels is False

    def test_preserved_frame(self):
        df = pd.DataFrame(
            {"A": [1, 2], "B": [3, 4]}, index=["a", "b"], allows_duplicate_labels=False
        )
        assert df.loc[["a"]].allows_duplicate_labels is False
        assert df.loc[:, ["A", "B"]].allows_duplicate_labels is False

    @not_implemented
    def test_to_frame(self):
        s = pd.Series(dtype=float, allows_duplicate_labels=False)
        assert s.to_frame().allows_duplicate_labels is False

    @pytest.mark.parametrize("func", ["add", "sub"])
    @pytest.mark.parametrize(
        "frame", [False, pytest.param(True, marks=not_implemented)]
    )
    @pytest.mark.parametrize("other", [1, pd.Series([1, 2], name="A")])
    def test_binops(self, func, other, frame):
        df = pd.Series(
            [1, 2], name="A", index=["a", "b"], allows_duplicate_labels=False
        )
        if frame:
            df = df.to_frame()
        if isinstance(other, pd.Series) and frame:
            other = other.to_frame()
        func = operator.methodcaller(func, other)
        assert df.allows_duplicate_labels is False
        assert func(df).allows_duplicate_labels is False

    @not_implemented
    def test_preserve_getitem(self):
        df = pd.DataFrame({"A": [1, 2]}, allows_duplicate_labels=False)
        assert df[["A"]].allows_duplicate_labels is False
        assert df["A"].allows_duplicate_labels is False
        assert df.loc[0].allows_duplicate_labels is False
        assert df.loc[[0]].allows_duplicate_labels is False
        assert df.loc[0, ["A"]].allows_duplicate_labels is False

    @pytest.mark.xfail(reason="Unclear behavior.")
    def test_ndframe_getitem_caching_issue(self):
        # NDFrame.__getitem__ will cache the first df['A']. May need to
        # invalidate that cache? Update the cached entries?
        df = pd.DataFrame({"A": [0]}, allows_duplicate_labels=False)
        assert df["A"].allows_duplicate_labels is False
        df.allows_duplicate_labels = True
        assert df["A"].allows_duplicate_labels is True

    @pytest.mark.parametrize(
        "objs, kwargs",
        [
            # Series
            (
                [
                    pd.Series(1, index=["a", "b"], allows_duplicate_labels=False),
                    pd.Series(2, index=["c", "d"], allows_duplicate_labels=False),
                ],
                {},
            ),
            (
                [
                    pd.Series(1, index=["a", "b"], allows_duplicate_labels=False),
                    pd.Series(2, index=["a", "b"], allows_duplicate_labels=False),
                ],
                {"ignore_index": True},
            ),
            (
                [
                    pd.Series(1, index=["a", "b"], allows_duplicate_labels=False),
                    pd.Series(2, index=["a", "b"], allows_duplicate_labels=False),
                ],
                {"axis": 1},
            ),
            # Frame
            (
                [
                    pd.DataFrame(
                        {"A": [1, 2]}, index=["a", "b"], allows_duplicate_labels=False
                    ),
                    pd.DataFrame(
                        {"A": [1, 2]}, index=["c", "d"], allows_duplicate_labels=False
                    ),
                ],
                {},
            ),
            (
                [
                    pd.DataFrame(
                        {"A": [1, 2]}, index=["a", "b"], allows_duplicate_labels=False
                    ),
                    pd.DataFrame(
                        {"A": [1, 2]}, index=["a", "b"], allows_duplicate_labels=False
                    ),
                ],
                {"ignore_index": True},
            ),
            (
                [
                    pd.DataFrame(
                        {"A": [1, 2]}, index=["a", "b"], allows_duplicate_labels=False
                    ),
                    pd.DataFrame(
                        {"B": [1, 2]}, index=["a", "b"], allows_duplicate_labels=False
                    ),
                ],
                {"axis": 1},
            ),
            # Series / Frame
            (
                [
                    pd.DataFrame(
                        {"A": [1, 2]}, index=["a", "b"], allows_duplicate_labels=False
                    ),
                    pd.Series(
                        [1, 2],
                        index=["a", "b"],
                        name="B",
                        allows_duplicate_labels=False,
                    ),
                ],
                {"axis": 1},
            ),
        ],
    )
    def test_concat(self, objs, kwargs):
        result = pd.concat(objs, **kwargs)
        assert result.allows_duplicate_labels is False

    @pytest.mark.parametrize(
        "left, right, kwargs, expected",
        [
            # false false false
            pytest.param(
                pd.DataFrame(
                    {"A": [0, 1]}, index=["a", "b"], allows_duplicate_labels=False
                ),
                pd.DataFrame(
                    {"B": [0, 1]}, index=["a", "d"], allows_duplicate_labels=False
                ),
                dict(left_index=True, right_index=True),
                False,
                marks=not_implemented,
            ),
            # false true false
            pytest.param(
                pd.DataFrame(
                    {"A": [0, 1]}, index=["a", "b"], allows_duplicate_labels=False
                ),
                pd.DataFrame({"B": [0, 1]}, index=["a", "d"]),
                dict(left_index=True, right_index=True),
                False,
                marks=not_implemented,
            ),
            # true true true
            (
                pd.DataFrame({"A": [0, 1]}, index=["a", "b"]),
                pd.DataFrame({"B": [0, 1]}, index=["a", "d"]),
                dict(left_index=True, right_index=True),
                True,
            ),
        ],
    )
    def test_merge(self, left, right, kwargs, expected):
        result = pd.merge(left, right, **kwargs)
        assert result.allows_duplicate_labels is expected

    @not_implemented
    def test_groupby(self):
        # XXX: This is under tested
        # TODO:
        #  - apply
        #  - transform
        #  - Should passing a grouper that disallows duplicates propagate?
        #    i.e. df.groupby(pd.Series([0, 1], allows_duplicate_labels=False))?
        df = pd.DataFrame({"A": [1, 2, 3]}, allows_duplicate_labels=False)
        result = df.groupby([0, 0, 1]).agg("count")
        assert result.allows_duplicate_labels is False

    @pytest.mark.parametrize("frame", [True, False])
    @not_implemented
    def test_window(self, frame):
        df = pd.Series(
            1,
            index=pd.date_range("2000", periods=12),
            name="A",
            allows_duplicate_labels=False,
        )
        if frame:
            df = df.to_frame()
        assert df.rolling(3).mean().allows_duplicate_labels is False
        assert df.ewm(3).mean().allows_duplicate_labels is False
        assert df.expanding(3).mean().allows_duplicate_labels is False


# ----------------------------------------------------------------------------
# Raises


class TestRaises:
    @pytest.mark.parametrize(
        "cls, axes",
        [
            (pd.Series, {"index": ["a", "a"], "dtype": float}),
            (pd.DataFrame, {"index": ["a", "a"]}),
            (pd.DataFrame, {"index": ["a", "a"], "columns": ["b", "b"]}),
            (pd.DataFrame, {"columns": ["b", "b"]}),
        ],
    )
    def test_construction_with_duplicates(self, cls, axes):
        result = cls(**axes)
        assert result.allows_duplicate_labels is True

        with pytest.raises(pd.errors.DuplicateLabelError):
            cls(**axes, allows_duplicate_labels=False)

    @pytest.mark.parametrize(
        "data",
        [
            pd.Series(index=[0, 0], dtype=float),
            pd.DataFrame(index=[0, 0]),
            pd.DataFrame(columns=[0, 0]),
        ],
    )
    def test_setting_allows_duplicate_labels_raises(self, data):
        with pytest.raises(pd.errors.DuplicateLabelError):
            data.allows_duplicate_labels = False

        assert data.allows_duplicate_labels is True

    @pytest.mark.parametrize(
        "func", [operator.methodcaller("append", pd.Series(0, index=["a", "b"]))]
    )
    def test_series_raises(self, func):
        s = pd.Series([0, 1], index=["a", "b"], allows_duplicate_labels=False)
        with pytest.raises(pd.errors.DuplicateLabelError):
            func(s)

    @pytest.mark.parametrize(
        "getter, target",
        [
            (operator.itemgetter(["A", "A"]), None),
            # loc
            (operator.itemgetter(["a", "a"]), "loc"),
            pytest.param(
                operator.itemgetter(("a", ["A", "A"])), "loc", marks=not_implemented
            ),
            pytest.param(
                operator.itemgetter((["a", "a"], "A")), "loc", marks=not_implemented
            ),
            # iloc
            (operator.itemgetter([0, 0]), "iloc"),
            pytest.param(
                operator.itemgetter((0, [0, 0])), "iloc", marks=not_implemented
            ),
            pytest.param(
                operator.itemgetter(([0, 0], 0)), "iloc", marks=not_implemented
            ),
        ],
    )
    def test_getitem_raises(self, getter, target):
        df = pd.DataFrame(
            {"A": [1, 2], "B": [3, 4]}, index=["a", "b"], allows_duplicate_labels=False
        )
        if target:
            # df, df.loc, or df.iloc
            target = getattr(df, target)
        else:
            target = df

        with pytest.raises(pd.errors.DuplicateLabelError):
            getter(target)

    @pytest.mark.parametrize(
        "objs, kwargs",
        [
            (
                [
                    pd.Series(1, index=[0, 1], name="a", allows_duplicate_labels=False),
                    pd.Series(2, index=[0, 1], name="a", allows_duplicate_labels=False),
                ],
                {"axis": 1},
            )
        ],
    )
    def test_concat_raises(self, objs, kwargs):
        with pytest.raises(pd.errors.DuplicateLabelError):
            pd.concat(objs, **kwargs)

    @not_implemented
    def test_merge_raises(self):
        a = pd.DataFrame(
            {"A": [0, 1, 2]}, index=["a", "b", "c"], allows_duplicate_labels=False
        )
        b = pd.DataFrame({"B": [0, 1, 2]}, index=["a", "b", "b"])
        with pytest.raises(pd.errors.DuplicateLabelError):
            pd.merge(a, b, left_index=True, right_index=True)


@pytest.mark.parametrize(
    "idx",
    [
        pd.Index([1, 1]),
        pd.Index(["a", "a"]),
        pd.Index([1.1, 1.1]),
        pd.PeriodIndex([pd.Period("2000", "D")] * 2),
        pd.DatetimeIndex([pd.Timestamp("2000")] * 2),
        pd.TimedeltaIndex([pd.Timedelta("1D")] * 2),
        pd.CategoricalIndex(["a", "a"]),
        pd.IntervalIndex([pd.Interval(0, 1)] * 2),
        pd.MultiIndex.from_tuples([("a", 1), ("a", 1)]),
    ],
    ids=lambda x: type(x).__name__,
)
def test_raises_basic(idx):
    with pytest.raises(pd.errors.DuplicateLabelError):
        pd.Series(1, index=idx, allows_duplicate_labels=False)

    with pytest.raises(pd.errors.DuplicateLabelError):
        pd.DataFrame({"A": [1, 1]}, index=idx, allows_duplicate_labels=False)

    with pytest.raises(pd.errors.DuplicateLabelError):
        pd.DataFrame([[1, 2]], columns=idx, allows_duplicate_labels=False)


def test_format_duplicate_labels_message():
    idx = pd.Index(["a", "b", "a", "b", "c"])
    result = idx._format_duplicate_message()
    expected = pd.DataFrame(
        {"positions": [[0, 2], [1, 3]]}, index=pd.Index(["a", "b"], name="label")
    )
    tm.assert_frame_equal(result, expected)


def test_format_duplicate_labels_message_multi():
    idx = pd.MultiIndex.from_product([["A"], ["a", "b", "a", "b", "c"]])
    result = idx._format_duplicate_message()
    expected = pd.DataFrame(
        {"positions": [[0, 2], [1, 3]]},
        index=pd.MultiIndex.from_product([["A"], ["a", "b"]]),
    )
    tm.assert_frame_equal(result, expected)


def test_dataframe_insert_raises():
    df = pd.DataFrame({"A": [1, 2]}, allows_duplicate_labels=False)
    with pytest.raises(ValueError, match="Cannot specify"):
        df.insert(0, "A", [3, 4], allow_duplicates=True)


@pytest.mark.parametrize(
    "method, frame_only",
    [
        (operator.methodcaller("set_index", "A", inplace=True), True),
        (operator.methodcaller("set_axis", ["A", "B"], inplace=True), False),
        (operator.methodcaller("reset_index", inplace=True), True),
        (operator.methodcaller("rename", lambda x: x, inplace=True), False),
    ],
)
def test_inplace_raises(method, frame_only):
    df = pd.DataFrame({"A": [0, 0], "B": [1, 2]}, allows_duplicate_labels=False)
    s = df["A"]
    s.allows_duplicate_labels = False
    msg = "Cannot specify"

    with pytest.raises(ValueError, match=msg):
        method(df)
    if not frame_only:
        with pytest.raises(ValueError, match=msg):
            method(s)
