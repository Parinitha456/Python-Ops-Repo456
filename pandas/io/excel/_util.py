import warnings

import pandas.compat as compat
from pandas.compat import lrange, range

from pandas.core.dtypes.common import is_integer, is_list_like

_writers = {}


def register_writer(klass):
    """
    Add engine to the excel writer registry. You must use this method to
    integrate with ``to_excel``.

    Parameters
    ----------
    klass : class
        Instance of ExcelWriter

    Returns
    -------
    None

    """

    if not callable(klass):
        raise ValueError("Can only register callables as engines")
    engine_name = klass.engine
    _writers[engine_name] = klass


def _get_default_writer(ext):
    """
    Return the default writer for the given extension.

    Parameters
    ----------
    ext : str
        The excel file extension for which to get the default engine.

    Returns
    -------
    engine : str
        The default engine for the extension.

    """
    _default_writers = {'xlsx': 'openpyxl', 'xlsm': 'openpyxl', 'xls': 'xlwt'}
    try:
        import xlsxwriter  # noqa
        _default_writers['xlsx'] = 'xlsxwriter'
    except ImportError:
        pass
    return _default_writers[ext]


def get_writer(engine_name):
    try:
        return _writers[engine_name]
    except KeyError:
        raise ValueError("No Excel writer '{engine}'"
                         .format(engine=engine_name))


def _excel2num(x):
    """
    Convert Excel column name like 'AB' to 0-based column index.

    Parameters
    ----------
    x : str
        The Excel column name to convert to a 0-based column index.

    Returns
    -------
    num : int
        The column index corresponding to the name.

    Raises
    ------
    ValueError
        Part of the Excel column name was invalid.
    """
    index = 0

    for c in x.upper().strip():
        cp = ord(c)

        if cp < ord("A") or cp > ord("Z"):
            raise ValueError("Invalid column name: {x}".format(x=x))

        index = index * 26 + cp - ord("A") + 1

    return index - 1


def _range2cols(areas):
    """
    Convert comma separated list of column names and ranges to indices.

    Parameters
    ----------
    areas : str
        A string containing a sequence of column ranges (or areas).

    Returns
    -------
    cols : list
        A list of 0-based column indices.

    Examples
    --------
    >>> _range2cols('A:E')
    [0, 1, 2, 3, 4]
    >>> _range2cols('A,C,Z:AB')
    [0, 2, 25, 26, 27]
    """
    cols = []

    for rng in areas.split(","):
        if ":" in rng:
            rng = rng.split(":")
            cols.extend(lrange(_excel2num(rng[0]), _excel2num(rng[1]) + 1))
        else:
            cols.append(_excel2num(rng))

    return cols


def _maybe_convert_usecols(usecols):
    """
    Convert `usecols` into a compatible format for parsing in `parsers.py`.

    Parameters
    ----------
    usecols : object
        The use-columns object to potentially convert.

    Returns
    -------
    converted : object
        The compatible format of `usecols`.
    """
    if usecols is None:
        return usecols

    if is_integer(usecols):
        warnings.warn(("Passing in an integer for `usecols` has been "
                       "deprecated. Please pass in a list of int from "
                       "0 to `usecols` inclusive instead."),
                      FutureWarning, stacklevel=2)
        return lrange(usecols + 1)

    if isinstance(usecols, compat.string_types):
        return _range2cols(usecols)

    return usecols


def _validate_freeze_panes(freeze_panes):
    if freeze_panes is not None:
        if (
            len(freeze_panes) == 2 and
            all(isinstance(item, int) for item in freeze_panes)
        ):
            return True

        raise ValueError("freeze_panes must be of form (row, column)"
                         " where row and column are integers")

    # freeze_panes wasn't specified, return False so it won't be applied
    # to output sheet
    return False


def _trim_excel_header(row):
    # trim header row so auto-index inference works
    # xlrd uses '' , openpyxl None
    while len(row) > 0 and (row[0] == '' or row[0] is None):
        row = row[1:]
    return row


def _maybe_convert_to_string(row):
    """
    Convert elements in a row to string from Unicode.

    This is purely a Python 2.x patch and is performed ONLY when all
    elements of the row are string-like.

    Parameters
    ----------
    row : array-like
        The row of data to convert.

    Returns
    -------
    converted : array-like
    """
    if compat.PY2:
        converted = []

        for i in range(len(row)):
            if isinstance(row[i], compat.string_types):
                try:
                    converted.append(str(row[i]))
                except UnicodeEncodeError:
                    break
            else:
                break
        else:
            row = converted

    return row


def _fill_mi_header(row, control_row):
    """Forward fill blank entries in row but only inside the same parent index.

    Used for creating headers in Multiindex.
    Parameters
    ----------
    row : list
        List of items in a single row.
    control_row : list of bool
        Helps to determine if particular column is in same parent index as the
        previous value. Used to stop propagation of empty cells between
        different indexes.

    Returns
    ----------
    Returns changed row and control_row
    """
    last = row[0]
    for i in range(1, len(row)):
        if not control_row[i]:
            last = row[i]

        if row[i] == '' or row[i] is None:
            row[i] = last
        else:
            control_row[i] = False
            last = row[i]

    return _maybe_convert_to_string(row), control_row


def _pop_header_name(row, index_col):
    """
    Pop the header name for MultiIndex parsing.

    Parameters
    ----------
    row : list
        The data row to parse for the header name.
    index_col : int, list
        The index columns for our data. Assumed to be non-null.

    Returns
    -------
    header_name : str
        The extracted header name.
    trimmed_row : list
        The original data row with the header name removed.
    """
    # Pop out header name and fill w/blank.
    i = index_col if not is_list_like(index_col) else max(index_col)

    header_name = row[i]
    header_name = None if header_name == "" else header_name

    return header_name, row[:i] + [''] + row[i + 1:]
