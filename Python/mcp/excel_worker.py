import win32com.client
from fastmcp import FastMCP
from typing import Any, List, Union

mcp = FastMCP("Excel-Live-Controller")

def get_excel_app():
    """실행 중인 Excel 인스턴스를 가져옵니다."""
    try:
        app = win32com.client.GetActiveObject("Excel.Application")
        return app
    except Exception as e:
        raise RuntimeError("실행 중인 Excel 인스턴스를 찾을 수 없습니다. Excel을 먼저 실행해주세요.") from e

def get_target_sheet(wb_name: str | None = None, sheet_name: str | None = None):
    """지정된 워크북 및 시트 또는 활성 시트를 반환합니다."""
    app = get_excel_app()
    if wb_name:
        wb = app.Workbooks(wb_name)
    else:
        wb = app.ActiveWorkbook
        if not wb:
            raise ValueError("활성화된 워크북이 없습니다.")
    
    if sheet_name:
        sheet = wb.Worksheets(sheet_name)
    else:
        sheet = wb.ActiveSheet
    return sheet

@mcp.tool()
def list_workbooks() -> List[str]:
    """현재 열려 있는 모든 워크북(엑셀 파일) 이름 목록을 반환합니다."""
    app = get_excel_app()
    return [wb.Name for wb in app.Workbooks]

@mcp.tool()
def read_range(cell_range: str, wb_name: str | None = None, sheet_name: str | None = None) -> Any:
    """지정된 범위(예: 'A1:C5' 또는 'A1')의 셀 데이터를 읽어옵니다."""
    sheet = get_target_sheet(wb_name, sheet_name)
    data = sheet.Range(cell_range).Value
    # COM 튜플 데이터를 직렬화 가능한 리스트로 변환
    if isinstance(data, tuple):
        return [list(row) if isinstance(row, tuple) else row for row in data]
    return data

@mcp.tool()
def write_range(cell_range: str, values: Union[List[List[Any]], Any], wb_name: str | None = None, sheet_name: str | None = None) -> str:
    """지정된 셀 범위에 단일 값 또는 2차원 리스트 형태의 데이터를 씁니다."""
    sheet = get_target_sheet(wb_name, sheet_name)
    sheet.Range(cell_range).Value = values
    return f"성공적으로 {cell_range} 영역에 데이터를 작성했습니다."

@mcp.tool()
def set_formula(cell_range: str, formula: str, wb_name: str | None = None, sheet_name: str | None = None) -> str:
    """셀에 엑셀 수식(예: '=SUM(A1:A10)')을 입력합니다."""
    sheet = get_target_sheet(wb_name, sheet_name)
    sheet.Range(cell_range).Formula = formula
    return f"{cell_range} 셀에 수식 '{formula}' 적용 완료"

@mcp.tool()
def create_chart(
    data_range: str,
    chart_type: str = "xlColumnClustered",
    title: str = "Chart",
    left: int = 300,
    top: int = 50,
    width: int = 400,
    height: int = 250,
    wb_name: str | None = None,
    sheet_name: str | None = None
) -> str:
    """
    지정된 데이터 영역을 기반으로 차트를 생성합니다.
    - chart_type 지원: xlColumnClustered(기본값, 51), xlLine(4), xlPie(5), xlBarClustered(57)
    """
    chart_type_map = {
        "xlColumnClustered": 51,
        "xlLine": 4,
        "xlPie": 5,
        "xlBarClustered": 57
    }
    xl_type = chart_type_map.get(chart_type, 51)
    
    sheet = get_target_sheet(wb_name, sheet_name)
    chart_objects = sheet.ChartObjects()
    chart_obj = chart_objects.Add(Left=left, Top=top, Width=width, Height=height)
    chart = chart_obj.Chart
    
    chart.SetSourceData(Source=sheet.Range(data_range))
    chart.ChartType = xl_type
    chart.HasTitle = True
    chart.ChartTitle.Text = title
    
    return f"'{title}' 차트가 {data_range} 데이터를 바탕으로 생성되었습니다."

if __name__ == "__main__":
    # FastMCP HTTP Transport 실행 (127.0.0.1:8700)
    mcp.run(transport="http", host="127.0.0.1", port=8700)
