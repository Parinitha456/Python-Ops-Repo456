import numpy as np
import pytest

import pandas as pd
import pandas.testing as tm


@pytest.mark.parametrize("na_value", [np.nan, None])
@pytest.mark.parametrize(
    "dropna, tuples, outputs",
    [
        (
            True,
            [["A", "B"], ["B", "A"]],
            {"c": [13.0, 123.23], "d": [13.0, 123.0], "e": [13.0, 1.0]},
        ),
        (
            False,
            [["A", "B"], ["A", np.nan], ["B", "A"]],
            {
                "c": [13.0, 12.3, 123.23],
                "d": [13.0, 233.0, 123.0],
                "e": [13.0, 12.0, 1.0],
            },
        ),
    ],
)
def test_groupby_dropna_multi_index_dataframe_nan_in_one_group(
    na_value, dropna, tuples, outputs
):
    # GH 3729 this is to test that NA is in one group
    df_list = [
        ["A", "B", 12, 12, 12],
        ["A", na_value, 12.3, 233.0, 12],
        ["B", "A", 123.23, 123, 1],
        ["A", "B", 1, 1, 1.0],
    ]
    df = pd.DataFrame(df_list, columns=["a", "b", "c", "d", "e"])
    grouped = df.groupby(["a", "b"], dropna=dropna).sum()

    mi = pd.MultiIndex.from_tuples(tuples, names=list("ab"))
    expected = pd.DataFrame(outputs, index=mi)

    tm.assert_frame_equal(grouped, expected, check_index_type=False)


@pytest.mark.parametrize(
    "na_value1, na_value2", [(np.nan, np.nan), (None, None), (np.nan, None)]
)
@pytest.mark.parametrize(
    "dropna, tuples, outputs",
    [
        (
            True,
            [["A", "B"], ["B", "A"]],
            {"c": [12.0, 123.23], "d": [12.0, 123.0], "e": [12.0, 1.0]},
        ),
        (
            False,
            [["A", "B"], ["A", np.nan], ["B", "A"], [np.nan, "B"]],
            {
                "c": [12.0, 13.3, 123.23, 1.0],
                "d": [12.0, 234.0, 123.0, 1.0],
                "e": [12.0, 13.0, 1.0, 1.0],
            },
        ),
    ],
)
def test_groupby_dropna_multi_index_dataframe_nan_in_two_groups(
    na_value1, na_value2, dropna, tuples, outputs
):
    # GH 3729 this is to test that NA in different groups with different representations
    df_list = [
        ["A", "B", 12, 12, 12],
        ["A", na_value1, 12.3, 233.0, 12],
        ["B", "A", 123.23, 123, 1],
        [na_value2, "B", 1, 1, 1.0],
        ["A", na_value2, 1, 1, 1.0],
    ]
    df = pd.DataFrame(df_list, columns=["a", "b", "c", "d", "e"])
    grouped = df.groupby(["a", "b"], dropna=dropna).sum()

    mi = pd.MultiIndex.from_tuples(tuples, names=list("ab"))
    expected = pd.DataFrame(outputs, index=mi)

    tm.assert_frame_equal(grouped, expected, check_index_type=False)


@pytest.mark.parametrize(
    "dropna, idx, outputs",
    [
        (True, ["A", "B"], {"b": [123.23, 13.0], "c": [123.0, 13.0], "d": [1.0, 13.0]}),
        (
            False,
            ["A", "B", np.nan],
            {
                "b": [123.23, 13.0, 12.3],
                "c": [123.0, 13.0, 233.0],
                "d": [1.0, 13.0, 12.0],
            },
        ),
    ],
)
def test_groupby_dropna_normal_index_dataframe(dropna, idx, outputs):
    # GH 3729
    df_list = [
        ["B", 12, 12, 12],
        [None, 12.3, 233.0, 12],
        ["A", 123.23, 123, 1],
        ["B", 1, 1, 1.0],
    ]
    df = pd.DataFrame(df_list, columns=["a", "b", "c", "d"])
    grouped = df.groupby("a", dropna=dropna).sum()

    expected = pd.DataFrame(outputs, index=pd.Index(idx, dtype="object", name="a"))

    tm.assert_frame_equal(grouped, expected, check_index_type=False)


@pytest.mark.parametrize(
    "dropna, idx, expected",
    [
        (True, ["a", "a", "b", np.nan], pd.Series([3, 3], index=["a", "b"])),
        (
            False,
            ["a", "a", "b", np.nan],
            pd.Series([3, 3, 3], index=["a", "b", np.nan]),
        ),
    ],
)
def test_groupby_dropna_series_level(dropna, idx, expected):
    ser = pd.Series([1, 2, 3, 3], index=idx)

    result = ser.groupby(level=0, dropna=dropna).sum()
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "dropna, expected",
    [
        (True, pd.Series([210.0, 350.0], index=["a", "b"], name="Max Speed")),
        (
            False,
            pd.Series([210.0, 350.0, 20.0], index=["a", "b", np.nan], name="Max Speed"),
        ),
    ],
)
def test_groupby_dropna_series_by(dropna, expected):
    ser = pd.Series(
        [390.0, 350.0, 30.0, 20.0],
        index=["Falcon", "Falcon", "Parrot", "Parrot"],
        name="Max Speed",
    )

    result = ser.groupby(["a", "b", "a", np.nan], dropna=dropna).mean()
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "dropna, tuples, outputs",
    [
        (
            True,
            [["A", "B"], ["B", "A"]],
            {"c": [13.0, 123.23], "d": [12.0, 123.0], "e": [1.0, 1.0]},
        ),
        (
            False,
            [["A", "B"], ["A", np.nan], ["B", "A"]],
            {
                "c": [13.0, 12.3, 123.23],
                "d": [12.0, 233.0, 123.0],
                "e": [1.0, 12.0, 1.0],
            },
        ),
    ],
)
def test_groupby_dropna_multi_index_dataframe_agg(dropna, tuples, outputs):
    # GH 3729
    df_list = [
        ["A", "B", 12, 12, 12],
        ["A", None, 12.3, 233.0, 12],
        ["B", "A", 123.23, 123, 1],
        ["A", "B", 1, 1, 1.0],
    ]
    df = pd.DataFrame(df_list, columns=["a", "b", "c", "d", "e"])
    agg_dict = {"c": sum, "d": max, "e": "min"}
    grouped = df.groupby(["a", "b"], dropna=dropna).agg(agg_dict)

    mi = pd.MultiIndex.from_tuples(tuples, names=list("ab"))
    expected = pd.DataFrame(outputs, index=mi)

    tm.assert_frame_equal(grouped, expected, check_index_type=False)


@pytest.mark.parametrize(
    "na_value1, na_value2",
    [
        (np.nan, pd.NaT),
        (np.nan, np.nan),
        (pd.NaT, pd.NaT),
        (pd.NaT, None),
        (None, None),
        (None, np.nan),
    ],
)
@pytest.mark.parametrize(
    "dropna, values, indexes",
    [
        (True, [12, 3], [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-02-01")]),
        (
            False,
            [12, 3, 6],
            [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-02-01"), pd.NaT],
        ),
    ],
)
def test_groupby_dropna_datetime_data(na_value1, na_value2, dropna, values, indexes):
    # 3729
    df = pd.DataFrame(
        {
            "values": [1, 2, 3, 4, 5, 6],
            "dt": [
                pd.Timestamp("2020-01-01"),
                na_value1,
                pd.Timestamp("2020-02-01"),
                na_value2,
                pd.Timestamp("2020-01-01"),
                pd.Timestamp("2020-01-01"),
            ],
        }
    )
    grouped = df.groupby("dt", dropna=dropna).agg({"values": sum})
    expected = pd.DataFrame({"values": values}, index=pd.Index(indexes, name="dt"))

    tm.assert_frame_equal(grouped, expected)


@pytest.mark.parametrize(
    "na_value1, na_value2",
    [
        (np.nan, pd.NaT),
        (np.nan, np.nan),
        (pd.NaT, pd.NaT),
        (pd.NaT, None),
        (None, None),
        (None, np.nan),
    ],
)
@pytest.mark.parametrize(
    "dropna, values, indexes",
    [
        (True, [3, 12], [pd.Timedelta("-2 days"), pd.Timedelta("-1 days")]),
        (
            False,
            [3, 12, 6],
            [pd.Timedelta("-2 days"), pd.Timedelta("-1 days"), pd.NaT],
        ),
    ],
)
def test_groupby_dropna_timedelta_data(na_value1, na_value2, dropna, values, indexes):
    # 3729
    df = pd.DataFrame(
        {
            "values": [1, 2, 3, 4, 5, 6],
            "dt": [
                pd.Timedelta("-1 days"),
                na_value1,
                pd.Timedelta("-2 days"),
                na_value2,
                pd.Timedelta("-1 days"),
                pd.Timedelta("-1 days"),
            ],
        }
    )
    grouped = df.groupby("dt", dropna=dropna).agg({"values": sum})
    expected = pd.DataFrame({"values": values}, index=pd.Index(indexes, name="dt"))

    tm.assert_frame_equal(grouped, expected)


@pytest.mark.parametrize(
    "na_value1, na_value2",
    [
        (np.nan, pd.NaT),
        (np.nan, np.nan),
        (pd.NaT, pd.NaT),
        (pd.NaT, None),
        (None, None),
        (None, np.nan),
    ],
)
@pytest.mark.parametrize(
    "dropna, values, indexes",
    [
        (True, [12, 3], [pd.Period("2020-01-01"), pd.Period("2020-02-01")]),
        (
            False,
            [12, 3, 6],
            [pd.Period("2020-01-01"), pd.Period("2020-02-01"), pd.NaT],
        ),
    ],
)
def test_groupby_dropna_period_data(na_value1, na_value2, dropna, values, indexes):
    # 3729
    df = pd.DataFrame(
        {
            "values": [1, 2, 3, 4, 5, 6],
            "dt": [
                pd.Period("2020-01-01"),
                na_value1,
                pd.Period("2020-02-01"),
                na_value2,
                pd.Period("2020-01-01"),
                pd.Period("2020-01-01"),
            ],
        }
    )
    grouped = df.groupby("dt", dropna=dropna).agg({"values": sum})
    expected = pd.DataFrame({"values": values}, index=pd.Index(indexes, name="dt"))

    tm.assert_frame_equal(grouped, expected)
