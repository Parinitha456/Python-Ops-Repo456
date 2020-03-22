from collections import defaultdict
import datetime

# import pandas._libs.json as json

from pandas.io.excel._base import ExcelWriter

# from pandas.io.excel._util import _validate_freeze_panes

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell
from odf.text import P


class _ODSWriter(ExcelWriter):
    engine = "odf"
    supported_extensions = (".ods",)

    def __init__(self, path, engine=None, encoding=None, mode="w", **engine_kwargs):
        engine_kwargs["engine"] = engine

        if mode == "a":
            raise ValueError("Append mode is not supported with odf!")

        super().__init__(path, mode=mode, **engine_kwargs)

        if encoding is None:
            encoding = "ascii"
        self.book = OpenDocumentSpreadsheet()

    #        self.fm_datetime = xlwt.easyxf(num_format_str=self.datetime_format)
    #        self.fm_date = xlwt.easyxf(num_format_str=self.date_format)

    def save(self):
        """
        Save workbook to disk.
        """
        for sheet in self.sheets.values():
            self.book.spreadsheet.addElement(sheet)
        return self.book.save(self.path)

    def write_cells(
        self, cells, sheet_name=None, startrow=0, startcol=0, freeze_panes=None
    ):
        # Write the frame cells using odf

        sheet_name = self._get_sheet_name(sheet_name)

        if sheet_name in self.sheets:
            wks = self.sheets[sheet_name]
        else:
            wks = Table(name=sheet_name)
            self.sheets[sheet_name] = wks

        #        if _validate_freeze_panes(freeze_panes):
        #            wks.set_panes_frozen(True)
        #            wks.set_horz_split_pos(freeze_panes[0])
        #            wks.set_vert_split_pos(freeze_panes[1])

        style_dict = {}

        rows = defaultdict(TableRow)
        col_count = defaultdict(int)

        for cell in sorted(cells, key=lambda cell: (cell.row, cell.col)):
            attributes = {}
            print(cell.row, cell.col, cell.val, cell.mergestart, cell.mergeend)
            if cell.mergestart is not None and cell.mergeend is not None:
                attributes = {
                    "numberrowsspanned": max(1, cell.mergestart),
                    "numbercolumnsspanned": cell.mergeend,
                }
            # fill with empty cells if needed
            for _ in range(cell.col - col_count[cell.row]):
                rows[cell.row].addElement(TableCell())
                col_count[cell.row] += 1
            val, fmt = self._value_with_fmt(cell.val)
            print("type", type(val), "value", val)
            pvalue = value = val
            if isinstance(val, bool):
                value = str(val).lower()
                pvalue = str(val).upper()
            if isinstance(val, datetime.datetime):
                if val.time():
                    value = val.isoformat()
                    pvalue = val.strftime("%c")
                else:
                    value = val.strftime("%Y-%m-%d")
                    pvalue = val.strftime("%x")
                tc = TableCell(valuetype="date", datevalue=value, attributes=attributes)
            elif isinstance(val, datetime.date):
                value = val.strftime("%Y-%m-%d")
                pvalue = val.strftime("%x")
                tc = TableCell(valuetype="date", datevalue=value, attributes=attributes)
            else:
                class_to_cell_type = {
                    str: "string",
                    int: "float",
                    float: "float",
                    bool: "boolean",
                }
                tc = TableCell(
                    valuetype=class_to_cell_type[type(val)],
                    value=value,
                    attributes=attributes,
                )
            rows[cell.row].addElement(tc)
            col_count[cell.row] += 1
            p = P(text=pvalue)
            tc.addElement(p)
            """
            stylekey = json.dumps(cell.style)
            if fmt:
                stylekey += fmt

            if stylekey in style_dict:
                style = style_dict[stylekey]
            else:
                style = self._convert_to_style(cell.style, fmt)
                style_dict[stylekey] = style
        """
        for row_nr in range(max(rows.keys()) + 1):
            wks.addElement(rows[row_nr])

    @classmethod
    def _style_to_xlwt(
        cls, item, firstlevel: bool = True, field_sep=",", line_sep=";"
    ) -> str:
        """
        helper which recursively generate an xlwt easy style string
        for example:

            hstyle = {"font": {"bold": True},
            "border": {"top": "thin",
                    "right": "thin",
                    "bottom": "thin",
                    "left": "thin"},
            "align": {"horiz": "center"}}
            will be converted to
            font: bold on; \
                    border: top thin, right thin, bottom thin, left thin; \
                    align: horiz center;
        """
        if hasattr(item, "items"):
            if firstlevel:
                it = [
                    f"{key}: {cls._style_to_xlwt(value, False)}"
                    for key, value in item.items()
                ]
                out = f"{(line_sep).join(it)} "
                return out
            else:
                it = [
                    f"{key} {cls._style_to_xlwt(value, False)}"
                    for key, value in item.items()
                ]
                out = f"{(field_sep).join(it)} "
                return out
        else:
            item = f"{item}"
            item = item.replace("True", "on")
            item = item.replace("False", "off")
            return item

    @classmethod
    def _convert_to_style(cls, style_dict, num_format_str=None):
        """
        converts a style_dict to an xlwt style object

        Parameters
        ----------
        style_dict : style dictionary to convert
        num_format_str : optional number format string
        """
        import xlwt

        if style_dict:
            xlwt_stylestr = cls._style_to_xlwt(style_dict)
            style = xlwt.easyxf(xlwt_stylestr, field_sep=",", line_sep=";")
        else:
            style = xlwt.XFStyle()
        if num_format_str is not None:
            style.num_format_str = num_format_str

        return style
