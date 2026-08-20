"""Standalone FastMCP Server for Microsoft Excel.

This server provides Excel automation tools using xlwings and FastMCP,
completely independent of Django or pyhub internal frameworks.
"""

import asyncio
import csv
import gc
import json
import re
import sys
import unicodedata
from ast import literal_eval
from io import StringIO
from typing import Any, Literal, Optional, Union

import xlwings as xw
from pydantic import Field

try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Excel-MCP-Server")


# ==============================================================================
# Helper Utilities
# ==============================================================================

def normalize_text(text: str) -> str:
    """Normalize Unicode text to NFC form."""
    if not text:
        return text
    return unicodedata.normalize("NFC", text)


def json_dumps(json_data: Any) -> str:
    """Serialize data to JSON formatted string."""
    return json.dumps(json_data, ensure_ascii=False, default=str)


def json_loads(json_str: str) -> Union[dict, list, str]:
    """Parse JSON string with fallback to literal_eval."""
    if isinstance(json_str, (str, bytes)):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                return literal_eval(json_str)
            except (ValueError, SyntaxError):
                pass
    return json_str


def convert_to_csv(data: list[list[Any]]) -> str:
    """Convert 2D data matrix to CSV string format."""
    if not data:
        return ""
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(data)
    return output.getvalue()


def normalize_2d_data(data: list[list[Any]]) -> list[list[Any]]:
    """Normalize 2D list so that each row has the same number of columns."""
    if not isinstance(data, list) or not data:
        return data
    if not all(isinstance(row, list) for row in data):
        return data

    max_length = max(len(row) for row in data)
    return [row + [""] * (max_length - len(row)) for row in data]


def csv_loads(csv_str: str) -> list[list[str]]:
    """Convert CSV formatted string into 2D list."""
    if not csv_str.strip():
        return [[""]]

    csv_str = csv_str.replace("\\n", "\n")
    f = StringIO(csv_str)
    reader = csv.reader(f, dialect="excel")
    data = [row for row in reader]

    if not data:
        return [[""]]

    column_counts = {}
    for row in data:
        count = len(row)
        column_counts[count] = column_counts.get(count, 0) + 1

    expected_columns = max(column_counts.items(), key=lambda x: x[1])[0]
    total_rows = len(data)

    if column_counts[expected_columns] / total_rows >= 0.8:
        processed_data = []
        for row in data:
            if len(row) > expected_columns:
                new_row = row[: expected_columns - 1]
                new_row.append(",".join(row[expected_columns - 1 :]))
                processed_data.append(new_row)
            else:
                processed_data.append(row)
        data = processed_data

    return normalize_2d_data(data)


def cleanup_excel_com():
    """Clean up Excel COM references and trigger garbage collection."""
    gc.collect()
    if sys.platform == "win32":
        try:
            if hasattr(xw.apps, "_cache"):
                xw.apps._cache.clear()
        except Exception:
            pass


def get_sheet(book_name: Optional[str] = None, sheet_name: Optional[str] = None) -> xw.Sheet:
    """Get active or specified workbook and sheet."""
    book = xw.books[book_name] if book_name else xw.books.active
    sheet = book.sheets[sheet_name] if sheet_name else book.sheets.active
    return sheet


def get_range(
    sheet_range: str,
    book_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
    expand_mode: Optional[str] = None,
) -> xw.Range:
    """Retrieve an Excel range with optional expansion."""
    if sheet_range and "!" in sheet_range:
        parsed_sheet_name, sheet_range = sheet_range.split("!", 1)
        sheet_name = sheet_name or parsed_sheet_name

    if expand_mode:
        sheet_range = sheet_range.split(":", 1)[0]

    sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
    range_ = sheet.range(sheet_range) if sheet_range else sheet.used_range

    if expand_mode:
        range_ = range_.expand(mode=expand_mode)

    return range_


def fix_data(sheet_range: str, values: Union[str, list]) -> Union[str, list]:
    """Adjust 1D list into column vector if target range is column-oriented."""
    if (
        isinstance(values, str)
        or not isinstance(values, list)
        or (isinstance(values, list) and values and isinstance(values[0], list))
    ):
        return values

    range_pattern = r"(?:(?:'[^']+'|[a-zA-Z0-9_.\-]+)!)?(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6})(?::(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}))?"
    match = re.match(range_pattern, sheet_range)
    if not match:
        return values

    start_cell, end_cell = match.group(1), match.group(2)
    if not end_cell:
        return values

    start_col = re.search(r"[A-Z]+", start_cell).group(0)
    end_col = re.search(r"[A-Z]+", end_cell).group(0)
    start_row = re.search(r"[0-9]+", start_cell).group(0)
    end_row = re.search(r"[0-9]+", end_cell).group(0)

    if start_col == end_col and start_row != end_row:
        return [[val] for val in values]

    return values


# ==============================================================================
# MCP Tools - Workbook & Sheet Operations
# ==============================================================================

@mcp.tool()
async def excel_get_opened_workbooks() -> str:
    """Get a list of all open workbooks and their sheets in Excel."""
    def _run():
        try:
            return json_dumps(
                {
                    "books": [
                        {
                            "name": normalize_text(book.name),
                            "fullname": normalize_text(book.fullname),
                            "sheets": [
                                {
                                    "name": normalize_text(sheet.name),
                                    "index": sheet.index,
                                    "range": sheet.used_range.get_address(),
                                    "count": sheet.used_range.count,
                                    "shape": sheet.used_range.shape,
                                    "active": sheet == xw.sheets.active,
                                    "table_names": [table.name for table in sheet.tables],
                                }
                                for sheet in book.sheets
                            ],
                            "active": book == xw.books.active,
                        }
                        for book in xw.books
                    ]
                }
            )
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_get_values(
    sheet_range: str = Field(
        default="",
        description="Excel range to get data. If not specified, uses used range (e.g. 'A1', 'A1:C10').",
    ),
    book_name: str = Field(default="", description="Workbook name (optional)"),
    sheet_name: str = Field(default="", description="Sheet name (optional)"),
    expand_mode: str = Field(
        default="",
        description="Range expansion mode: 'table', 'down', 'right', or empty.",
    ),
    value_type: str = Field(
        default="values",
        description="Data type to retrieve: 'values' or 'formula2'.",
    ),
) -> str:
    """Read values or formulas from an Excel range."""
    def _run():
        try:
            range_ = get_range(
                sheet_range=sheet_range,
                book_name=book_name,
                sheet_name=sheet_name,
                expand_mode=expand_mode or None,
            )
            if value_type == "formula2":
                return json_dumps(range_.formula2)
            else:
                values = range_.value
                if values is None:
                    return ""
                elif not isinstance(values, list):
                    return str(values)
                elif values and not isinstance(values[0], list):
                    return convert_to_csv([values])
                else:
                    return convert_to_csv(values)
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_set_values(
    sheet_range: str = Field(description="Cell range to write (e.g. 'A1', 'A1:D10')"),
    values: Optional[str] = Field(default=None, description="CSV or JSON formatted values"),
    csv_abs_path: str = Field(default="", description="Absolute path to CSV file to load"),
    book_name: str = Field(default="", description="Workbook name (optional)"),
    sheet_name: str = Field(default="", description="Sheet name (optional)"),
) -> str:
    """Write data matrix to a specified range in Excel."""
    def _run():
        try:
            range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
            values_to_use = values

            if csv_abs_path:
                with open(csv_abs_path, "rt", encoding="utf-8") as f:
                    values_to_use = f.read()

            if not values_to_use:
                raise ValueError("Either 'values' or 'csv_abs_path' must be provided.")

            if values_to_use.strip().startswith(("[", "{")):
                parsed_data = json_loads(values_to_use)
            else:
                parsed_data = csv_loads(values_to_use)

            range_.value = fix_data(sheet_range, parsed_data)
            return f"Successfully set values to {range_.address}."
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_set_cell_data(
    data_type: Literal["values", "formula"] = Field(description="Data type: 'values' or 'formula'"),
    sheet_range: str = Field(description="Cell range (e.g. 'A1', 'B2:C10')"),
    data: str = Field(description="Values (CSV/JSON) or Formula starting with '='"),
    book_name: str = Field(default="", description="Workbook name (optional)"),
    sheet_name: str = Field(default="", description="Sheet name (optional)"),
) -> str:
    """Set cell value or Excel formula."""
    def _run():
        try:
            range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
            if data_type == "values":
                if data.strip().startswith(("[", "{")):
                    parsed = json_loads(data)
                else:
                    parsed = csv_loads(data)
                range_.value = fix_data(sheet_range, parsed)
                return f"Successfully set values to {range_.address}."
            elif data_type == "formula":
                if not data.startswith("="):
                    return json_dumps({"error": "Formula must start with '='" })
                range_.formula2 = data
                return f"Successfully set formula to {range_.address}."
            else:
                return json_dumps({"error": f"Unknown data_type: {data_type}"})
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_find_data_ranges(
    book_name: str = Field(default="", description="Workbook name (optional)"),
    sheet_name: str = Field(default="", description="Sheet name (optional)"),
) -> str:
    """Detect and return all contiguous data blocks in the sheet."""
    def _run():
        try:
            sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
            used_range = sheet.used_range
            if not used_range:
                return json_dumps([])

            values = used_range.value
            if not values:
                return json_dumps([])

            if not isinstance(values, list):
                values = [[values]]
            elif values and not isinstance(values[0], list):
                values = [values]

            data_ranges = []
            visited = set()

            for row_idx, row in enumerate(values):
                for col_idx, cell_value in enumerate(row):
                    if cell_value is not None and (row_idx, col_idx) not in visited:
                        cell = used_range.cells[row_idx, col_idx]
                        data_block = cell.expand("table")

                        block_start_row = data_block.row - used_range.row
                        block_start_col = data_block.column - used_range.column
                        block_rows = data_block.rows.count
                        block_cols = data_block.columns.count

                        for r in range(block_start_row, block_start_row + block_rows):
                            for c in range(block_start_col, block_start_col + block_cols):
                                visited.add((r, c))

                        data_ranges.append(data_block.get_address())

            return json_dumps(data_ranges)
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_set_styles(
    styles: str = Field(
        description="Style spec in single string format 'A1:B2;background_color=255,255,0;bold=true' or CSV format."
    ),
) -> str:
    """Apply formatting styles (background color, font color, bold, italic) to Excel cells."""
    def _run():
        def apply_styles(excel_range, style_data):
            bg_color = style_data.get("background_color")
            if bg_color:
                rgb = tuple(int(x.strip()) for x in bg_color.split(",")) if isinstance(bg_color, str) else bg_color
                excel_range.color = rgb

            font_color = style_data.get("font_color")
            if font_color:
                rgb = tuple(int(x.strip()) for x in font_color.split(",")) if isinstance(font_color, str) else font_color
                excel_range.font.color = rgb

            bold = style_data.get("bold")
            if bold is not None:
                excel_range.font.bold = str(bold).lower() == "true"

            italic = style_data.get("italic")
            if italic is not None:
                excel_range.font.italic = str(italic).lower() == "true"

        def parse_single_style(style_str):
            parts = style_str.split(";")
            range_spec = parts[0]
            book_name, sheet_name = "", ""
            if "!" in range_spec:
                sheet_part, range_spec = range_spec.split("!", 1)
                if ".xlsx" in sheet_part:
                    book_name = sheet_part
                else:
                    sheet_name = sheet_part

            options = {}
            for part in parts[1:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    options[k.strip()] = v.strip()

            return book_name, sheet_name, range_spec, options

        try:
            selected_ranges = []
            if "\n" in styles or styles.startswith("book_name,"):
                rows = csv_loads(styles)
                if rows and isinstance(rows[0], list):
                    headers = rows[0]
                    rows = [{headers[i]: row[i] for i in range(len(headers)) if i < len(row)} for row in rows[1:]]

                for row_data in rows:
                    excel_range = get_range(
                        sheet_range=row_data.get("range", ""),
                        book_name=row_data.get("book_name", ""),
                        sheet_name=row_data.get("sheet_name", ""),
                        expand_mode=row_data.get("expand_mode", ""),
                    )
                    apply_styles(excel_range, row_data)
                    selected_ranges.append(excel_range)
            else:
                book_name, sheet_name, range_spec, options = parse_single_style(styles)
                excel_range = get_range(
                    sheet_range=range_spec,
                    book_name=book_name,
                    sheet_name=sheet_name,
                    expand_mode=options.get("expand_mode", ""),
                )
                apply_styles(excel_range, options)
                selected_ranges.append(excel_range)

            addresses = ",".join(r.get_address() for r in selected_ranges)
            return f"Successfully set styles to {addresses}."
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_autofit(
    sheet_range: str = Field(default="", description="Range to autofit (e.g. 'A:E' or 'A1:D10')"),
    book_name: str = Field(default="", description="Workbook name (optional)"),
    sheet_name: str = Field(default="", description="Sheet name (optional)"),
) -> str:
    """Autofit column widths and row heights in specified range."""
    def _run():
        try:
            range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
            range_.autofit()
            return f"Successfully autofitted {range_.address}."
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_add_sheet(
    name: str = Field(default="", description="New sheet name (auto-generated if empty)"),
    book_name: str = Field(default="", description="Workbook name (optional)"),
    at_start: bool = Field(default=False, description="Add sheet at the beginning"),
    at_end: bool = Field(default=False, description="Add sheet at the end"),
) -> str:
    """Add a new sheet to an Excel workbook."""
    def _run():
        try:
            book = xw.books[book_name] if book_name else xw.books.active
            before = book.sheets[0] if at_start and len(book.sheets) > 0 else None
            after = book.sheets[-1] if at_end and len(book.sheets) > 0 else None

            sheet = book.sheets.add(name=name or None, before=before, after=after)
            return f"Successfully created sheet: {sheet.name}"
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


# ==============================================================================
# MCP Tools - Tables, Charts & Pivot Tables
# ==============================================================================

@mcp.tool()
async def excel_convert_to_table(
    sheet_range: str = Field(description="Range to convert to Table (e.g. 'A1:D10')"),
    table_name: str = Field(default="", description="Table name (auto-generated if empty)"),
    book_name: str = Field(default="", description="Workbook name (optional)"),
    sheet_name: str = Field(default="", description="Sheet name (optional)"),
    table_style_name: str = Field(default="TableStyleMedium2", description="Excel table style name"),
) -> str:
    """Convert an Excel range to a structured Table/ListObject."""
    def _run():
        try:
            range_ = get_range(sheet_range=sheet_range, book_name=book_name, sheet_name=sheet_name)
            sheet = range_.sheet
            table = sheet.tables.add(
                source_range=range_,
                name=table_name or None,
                table_style_name=table_style_name,
            )
            return f"Successfully converted range to table: {table.name}"
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_get_charts(
    book_name: str = Field(default="", description="Workbook name (optional)"),
    sheet_name: str = Field(default="", description="Sheet name (optional)"),
) -> str:
    """List all charts in the specified sheet."""
    def _run():
        try:
            sheet = get_sheet(book_name=book_name, sheet_name=sheet_name)
            return json_dumps(
                [
                    {
                        "name": chart.name,
                        "left": chart.left,
                        "top": chart.top,
                        "width": chart.width,
                        "height": chart.height,
                        "index": i,
                    }
                    for i, chart in enumerate(sheet.charts)
                ]
            )
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_add_chart(
    source_sheet_range: str = Field(description="Data range for chart (e.g. 'A1:B10')"),
    dest_sheet_range: str = Field(description="Top-left cell where chart will be placed (e.g. 'D2')"),
    chart_type: str = Field(default="line", description="Chart type (line, column_clustered, bar_clustered, pie, etc.)"),
    name: str = Field(default="", description="Chart name (optional)"),
    source_book_name: str = Field(default="", description="Source workbook (optional)"),
    source_sheet_name: str = Field(default="", description="Source sheet (optional)"),
    dest_book_name: str = Field(default="", description="Destination workbook (optional)"),
    dest_sheet_name: str = Field(default="", description="Destination sheet (optional)"),
) -> str:
    """Add a chart to an Excel sheet."""
    def _run():
        try:
            source_range = get_range(
                sheet_range=source_sheet_range,
                book_name=source_book_name,
                sheet_name=source_sheet_name,
            )
            dest_range = get_range(
                sheet_range=dest_sheet_range,
                book_name=dest_book_name,
                sheet_name=dest_sheet_name,
            )

            dest_sheet = dest_range.sheet
            chart = dest_sheet.charts.add(
                left=dest_range.left,
                top=dest_range.top,
                width=375,
                height=225,
            )
            chart.chart_type = chart_type
            chart.set_source_data(source_range)
            if name:
                chart.name = name

            return f"Successfully created chart: {chart.name}"
        finally:
            cleanup_excel_com()

    return await asyncio.to_thread(_run)


@mcp.tool()
async def excel_get_info(
    info_type: Literal["workbooks", "charts"] = Field(description="Information type: 'workbooks' or 'charts'"),
    book_name: str = Field(default="", description="Workbook name (optional)"),
    sheet_name: str = Field(default="", description="Sheet name (optional)"),
) -> str:
    """Unified tool to get metadata about open workbooks or charts."""
    if info_type == "workbooks":
        return await excel_get_opened_workbooks()
    elif info_type == "charts":
        return await excel_get_charts(book_name=book_name, sheet_name=sheet_name)
    else:
        return json_dumps({"error": f"Unknown info_type: {info_type}"})


# ==============================================================================
# Server Entry Point
# ==============================================================================

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8001

    if hasattr(mcp, "run_sse"):
        mcp.run_sse(host=host, port=port)
    elif hasattr(mcp, "settings"):
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        try:
            mcp.run(transport="sse", host=host, port=port)
        except TypeError:
            try:
                mcp.run(transport="sse", port=port)
            except TypeError:
                mcp.run(transport="sse")
