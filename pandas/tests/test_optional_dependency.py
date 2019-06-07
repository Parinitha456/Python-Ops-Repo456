import sys
import types

import pytest

from pandas.compat._optional import VERSIONS, import_optional_dependency

import pandas.util.testing as tm


def test_import_optional():
    match = "Missing .*notapackage.* pip .* conda .* notapackage"
    with pytest.raises(ImportError, match=match):
        import_optional_dependency("notapackage")

    result = import_optional_dependency("notapackage", raise_on_missing=False)
    assert result is None


def test_xlrd_version_fallback():
    pytest.importorskip('xlrd')
    import_optional_dependency("xlrd")


def test_bad_version():
    name = 'fakemodule'
    module = types.ModuleType(name)
    module.__version__ = "0.9.0"
    sys.modules[name] = module
    VERSIONS[name] = '1.0.0'

    match = "Pandas requires .*1.0.0.* of .fakemodule.*'0.9.0'"
    with pytest.raises(ImportError, match=match):
        import_optional_dependency("fakemodule")

    with tm.assert_produces_warning(UserWarning):
        result = import_optional_dependency("fakemodule", on_version="warn")
    assert result is None
