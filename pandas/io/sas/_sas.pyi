from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pandas.io.sas.sas7bdat import SAS7BDATReader

class Parser:
    def __init__(self, parser: SAS7BDATReader) -> None: ...
    def read(self, nrows: int) -> None: ...

def get_subheader_index(signature: bytes) -> int: ...
