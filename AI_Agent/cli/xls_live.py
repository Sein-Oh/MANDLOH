import io
import sys
import gc
import json
import math
import click
import win32com.client

# UTF-8 콘솔 입출력 보장
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

HOW_TO_USE_DOC = """# Excel Automation CLI Tool Guide for LLMs & Operators

이 도구는 현재 Windows에서 **실행 중인 Microsoft Excel 인스턴스**와 상호작용하는 실시간 보조 CLI 앱입니다.

## 기본 동작 원리
- \`GetActiveObject("Excel.Application")\`을 통해 활성 워크북에 즉시 연결됩니다.
- 셀 좌표 표기는 'A1', 'A1:C10'뿐 아니라 '행,열' 형태(예: '3,2')도 지원합니다.
- 값 입력 시 정수, 실수, 불리언 타입이 자동 변환됩니다.

## 지원 차트 타입 (Chart Types)
- \`scatter\` / \`xy\`: 기본 점 분산형 (xlXYScatter, -4169)
- \`scatter-smooth\`: 부드러운 곡선 분산형 (xlXYScatterSmooth, 72)
- \`scatter-smooth-nomarkers\`: 마커 없는 곡선 분산형 (xlXYScatterSmoothNoMarkers, 73)
- \`scatter-line\`: 직선 연결 분산형 (xlXYScatterLines, 74)
- \`line\`: 꺾은선형 (xlLine, 4)
- \`column\`: 묶은 세로 막대형 (xlColumnClustered, 51)
- \`bar\`: 묶은 가로 막대형 (xlBarClustered, 57)
- \`pie\`: 원형 (xlPie, 5)
- \`area\`: 영역형 (xlArea, 1)

## 주요 명령어 요약

| Command | Arguments | Options | Description |
|---|---|---|---|
| \`list\` | None | \`-s, --sheet\` | 지정 시트(또는 활성 시트) 데이터 영역 출력 |
| \`edit\` | \`<cell>\` \`<val>\` | \`-s\`, \`-c, --color\`, \`-w, --save\` | 단일 셀 값 및 글꼴 색상 변경 |
| \`write-batch\` | \`<start_cell>\` \`<data>\` | \`-s\`, \`-w, --save\` | 2차원 리스트 데이터 일괄 고속 입력 |
| \`generate-math\`| None | \`--expr\`, \`--start\`, \`--end\`, \`--points\`, \`--start-cell\`, \`-s\`, \`-w\` | 수학 함수(사인곡선 등) 데이터 자동 생성 |
| \`insert\` | \`<row>\` \`<data>\` | \`-s\`, \`-w, --save\` | 특정 행에 쉼표 구분 데이터 삽입 |
| \`clear\` | \`<cell>\` | \`-s\`, \`-w, --save\` | 셀/영역 내용 삭제 |
| \`formula\` | \`<cell>\` \`<formula>\` | \`-s\`, \`-w, --save\` | 계산 수식 입력 (선두 '=' 자동 보정) |
| \`chart\` | \`<range>\` | \`-s\`, \`--type\`, \`--name\`, \`--pos\`, \`--size\`, \`-w\` | 데이터 범위 기반 차트 생성 |
| \`update-chart\` | \`<index>\` | \`-s\`, \`--title\`, \`--type\`, \`--pos\`, \`--size\`, \`-w\` | 기존 차트(0-index) 속성 변경 |
| \`save\` | None | None | 현재 작업 중인 통합 문서 즉시 저장 |
"""

class ExcelControllerFast:
    COLOR_MAP = {
        'black': 0,
        'white': 16777215,
        'red': 255,
        'green': 65280,
        'blue': 16711680,
        'yellow': 65535,
        'gray': 8421504,
    }

    CHART_TYPE_MAP = {
        'scatter': -4169,
        'xy': -4169,
        'scatter-smooth': 72,
        'scatter-smooth-nomarkers': 73,
        'scatter-line': 74,
        'scatter-lines': 74,
        'scatter-line-nomarkers': 75,
        'line': 4,
        'line-markers': 65,
        'column': 51,
        'bar': 57,
        'pie': 5,
        'area': 1,
        'area-stacked': 76,
    }

    def __init__(self):
        self.app = None
        self.wb = None

    def connect(self) -> bool:
        try:
            self.app = win32com.client.GetActiveObject("Excel.Application")
            self.wb = self.app.ActiveWorkbook
            if self.wb is None:
                click.secho("[Error] Excel이 실행 중이지만 열려 있는 워크북이 없습니다.", fg="red")
                return False
            return True
        except Exception:
            return False

    def close(self):
        self.wb = None
        self.app = None
        gc.collect()

    def _get_sheet(self, sheet_name=None):
        if sheet_name:
            return self.wb.Worksheets(sheet_name)
        return self.wb.ActiveSheet

    def _get_range(self, sheet, cell_ref: str):
        cell_ref = cell_ref.strip()
        if ',' in cell_ref and ':' not in cell_ref:
            parts = cell_ref.split(',')
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                r, c = int(parts[0].strip()), int(parts[1].strip())
                return sheet.Cells(r, c)
        return sheet.Range(cell_ref)

    @staticmethod
    def _parse_value(value_str):
        if not isinstance(value_str, str):
            return value_str
        val = value_str.strip()
        if val.lower() == 'true':
            return True
        if val.lower() == 'false':
            return False
        if val.lower() in ('none', 'null', ''):
            return None
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            pass
        return val

    def save(self):
        try:
            self.wb.Save()
            click.secho(f"[Success] Workbook '{self.wb.Name}' saved successfully.", fg="green")
        except Exception as e:
            click.secho(f"[Error] Failed to save workbook: {e}", fg="red")

    def list_content(self, sheet_name=None):
        try:
            sheet = self._get_sheet(sheet_name)
            click.echo(f"\\n--- Workbook: {self.wb.Name} | Sheet: {sheet.Name} ---")
            used_range = sheet.UsedRange
            start_row = used_range.Row
            start_col = used_range.Column
            row_count = used_range.Rows.Count
            col_count = used_range.Columns.Count

            if row_count == 0 or col_count == 0:
                click.echo("(Empty Sheet)")
                return

            end_row = start_row + row_count - 1
            end_col = start_col + col_count - 1
            data_range = sheet.Range(sheet.Cells(start_row, start_col), sheet.Cells(end_row, end_col))
            values = data_range.Value

            if values is not None:
                if not isinstance(values, tuple):
                    values = ((values,),)
                elif not isinstance(values[0], tuple):
                    values = (values,)

                found_any = False
                for r_idx, row in enumerate(values, start=start_row):
                    row_output = []
                    for c_idx, val in enumerate(row, start=start_col):
                        if val is not None and str(val).strip() != "":
                            row_output.append(f"[{r_idx},{c_idx}] {val}")
                            found_any = True
                    if row_output:
                        click.echo(" ".join(row_output))

                if not found_any:
                    click.echo("(No visible data found)")
            else:
                click.echo("(No visible data found)")
            click.echo("-" * 45)
        except Exception as e:
            click.secho(f"[Error] Failed to list content: {e}", fg="red")

    def edit_cell(self, cell_ref: str, new_value: str, color_name='black', sheet_name=None, save=False):
        try:
            sheet = self._get_sheet(sheet_name)
            target = self._get_range(sheet, cell_ref)
            target.Value = self._parse_value(new_value)

            color_code = self.COLOR_MAP.get(color_name.lower())
            if color_code is not None:
                target.Font.Color = color_code

            click.echo(f"[Success] Updated {cell_ref} on [{sheet.Name}] to: {new_value}")
            if save:
                self.save()
        except Exception as e:
            click.secho(f"[Error] Failed to edit cell {cell_ref}: {e}", fg="red")

    def write_batch(self, start_cell: str, matrix_data: list, sheet_name=None, save=False):
        try:
            if not matrix_data or not isinstance(matrix_data, list):
                click.secho("[Error] Data must be a non-empty 2D list.", fg="red")
                return

            sheet = self._get_sheet(sheet_name)
            origin = self._get_range(sheet, start_cell)
            start_row = origin.Row
            start_col = origin.Column

            rows = len(matrix_data)
            cols = max(len(row) for row in matrix_data) if rows > 0 else 0

            formatted_grid = []
            for r in matrix_data:
                parsed_row = [self._parse_value(c) for c in r]
                if len(parsed_row) < cols:
                    parsed_row.extend([None] * (cols - len(parsed_row)))
                formatted_grid.append(tuple(parsed_row))

            target_range = sheet.Range(
                sheet.Cells(start_row, start_col),
                sheet.Cells(start_row + rows - 1, start_col + cols - 1)
            )
            target_range.Value = tuple(formatted_grid)

            click.echo(f"[Success] Wrote {rows} rows x {cols} cols starting from {start_cell} on [{sheet.Name}]")
            if save:
                self.save()
        except Exception as e:
            click.secho(f"[Error] Failed to batch write: {e}", fg="red")

    def insert_row(self, row_idx: int, data: str, sheet_name=None, save=False):
        try:
            sheet = self._get_sheet(sheet_name)
            sheet.Rows(row_idx).Insert()
            items = [self._parse_value(d) for d in data.split(',')]
            for c_idx, val in enumerate(items, start=1):
                if val is not None:
                    sheet.Cells(row_idx, c_idx).Value = val
            click.echo(f"[Success] Inserted row at {row_idx} on [{sheet.Name}]")
            if save:
                self.save()
        except Exception as e:
            click.secho(f"[Error] Failed to insert row: {e}", fg="red")

    def clear_content(self, cell_ref: str, sheet_name=None, save=False):
        try:
            sheet = self._get_sheet(sheet_name)
            target = self._get_range(sheet, cell_ref)
            target.ClearContents()
            click.echo(f"[Success] Cleared content in {cell_ref} on [{sheet.Name}]")
            if save:
                self.save()
        except Exception as e:
            click.secho(f"[Error] Failed to clear content: {e}", fg="red")

    def set_formula(self, cell_ref: str, formula: str, sheet_name=None, save=False):
        try:
            sheet = self._get_sheet(sheet_name)
            target = self._get_range(sheet, cell_ref)
            if not formula.startswith('='):
                formula = '=' + formula
            target.Formula = formula
            click.echo(f"[Success] Set formula on {cell_ref}: {formula}")
            if save:
                self.save()
        except Exception as e:
            click.secho(f"[Error] Failed to set formula: {e}", fg="red")

    def create_chart(self, data_range_str: str, chart_type='scatter-smooth', title='My Chart',
                     left=120, top=50, width=450, height=260, sheet_name=None, save=False):
        try:
            sheet = self._get_sheet(sheet_name)
            chart_key = chart_type.lower().strip()
            xl_type = self.CHART_TYPE_MAP.get(chart_key, 72)

            data_range = sheet.Range(data_range_str)
            chart_obj = sheet.ChartObjects().Add(left, top, width, height)
            chart = chart_obj.Chart
            chart.ChartType = xl_type
            chart.SetSourceData(Source=data_range)
            chart.HasTitle = True
            chart.ChartTitle.Text = title
            click.echo(f"[Success] Created '{chart_key}' (Type ID: {xl_type}) chart for range {data_range_str}")
            if save:
                self.save()
        except Exception as e:
            click.secho(f"[Error] Failed to create chart: {e}", fg="red")

    def update_chart(self, index: int, title=None, chart_type=None,
                     left=None, top=None, width=None, height=None, sheet_name=None, save=False):
        try:
            sheet = self._get_sheet(sheet_name)
            chart_obj = sheet.ChartObjects(index + 1)
            chart = chart_obj.Chart

            if title:
                chart.HasTitle = True
                chart.ChartTitle.Text = title
                click.echo(f"Updated title -> {title}")
            if chart_type:
                chart_key = chart_type.lower().strip()
                if chart_key in self.CHART_TYPE_MAP:
                    xl_type = self.CHART_TYPE_MAP[chart_key]
                    chart.ChartType = xl_type
                    click.echo(f"Updated chart type -> {chart_key} (ID: {xl_type})")
                else:
                    click.secho(f"[Warning] Unknown chart type '{chart_type}'. Available: {list(self.CHART_TYPE_MAP.keys())}", fg="yellow")
            if left is not None and top is not None:
                chart_obj.Left = left
                chart_obj.Top = top
                click.echo(f"Updated position -> ({left}, {top})")
            if width is not None and height is not None:
                chart_obj.Width = width
                chart_obj.Height = height
                click.echo(f"Updated size -> {width} x {height}")

            click.echo(f"[Success] Updated chart #{index} on [{sheet.Name}]")
            if save:
                self.save()
        except Exception as e:
            click.secho(f"[Error] Failed to update chart #{index}: {e}", fg="red")


# --- CLI Commands ---

def print_how_to_use(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(HOW_TO_USE_DOC)
    ctx.exit(0)


@click.group()
@click.option('--how-to-use', is_flag=True, is_eager=True, expose_value=False, callback=print_how_to_use,
              help="Show LLM/Operator guide with command usage examples.")
@click.pass_context
def cli(ctx):
    controller = ExcelControllerFast()
    if not controller.connect():
        click.secho("[Error] Excel이 실행 중이지 않거나 열려 있는 워크북이 없습니다.", fg="red")
        ctx.exit(1)
    ctx.obj = controller
    ctx.call_on_close(controller.close)


@cli.command('list', short_help="시트의 데이터 영역 출력")
@click.option('-s', '--sheet', help="시트명 (생략 시 활성 시트)")
@click.pass_obj
def list_cmd(controller, sheet):
    controller.list_content(sheet)


@cli.command('edit', short_help="단일 셀 값/색상 수정")
@click.argument('cell_ref')
@click.argument('new_value')
@click.option('-s', '--sheet', help="시트명")
@click.option('-c', '--color', default='black', help="색상 (black, red, green, blue 등)")
@click.option('-w', '--save', is_flag=True, help="즉시 저장")
@click.pass_obj
def edit_cmd(controller, cell_ref, new_value, sheet, color, save):
    controller.edit_cell(cell_ref, new_value, color, sheet_name=sheet, save=save)


@cli.command('write-batch', short_help="2차원 배열/표 데이터 일괄 고속 입력")
@click.argument('start_cell')
@click.argument('raw_data')
@click.option('-s', '--sheet', help="시트명")
@click.option('-w', '--save', is_flag=True, help="입력 후 저장")
@click.pass_obj
def write_batch_cmd(controller, start_cell, raw_data, sheet, save):
    try:
        if raw_data.strip().startswith('['):
            grid = json.loads(raw_data)
        else:
            grid = []
            for line in raw_data.replace('\\\\n', '\\n').split('\\n'):
                line = line.strip()
                if line:
                    grid.append([col.strip() for col in line.split(',')])
        controller.write_batch(start_cell, grid, sheet_name=sheet, save=save)
    except Exception as e:
        click.secho(f"[Error] Failed to parse input data: {e}", fg="red")


@cli.command('generate-math', short_help="수학 함수 데이터를 생성하여 시트에 입력")
@click.option('--expr', default="math.sin(x)", help="파이썬 계산식 (예: 'math.sin(x)', 'math.cos(2*x)')")
@click.option('--start', 'start_val', default="0", help="시작 x 값 (예: '0', '0.0')")
@click.option('--end', 'end_val', default="4*math.pi", help="종료 x 값 (예: '4*math.pi' = 2주기)")
@click.option('--points', default=100, type=int, help="생성할 데이터 포인트 개수")
@click.option('--start-cell', default="A1", help="데이터가 시작될 셀 주소")
@click.option('--x-label', default="X", help="X 열 헤더")
@click.option('--y-label', default="Y", help="Y 열 헤더")
@click.option('-s', '--sheet', help="시트명")
@click.option('-w', '--save', is_flag=True, help="생성 후 저장")
@click.pass_obj
def generate_math_cmd(controller, expr, start_val, end_val, points, start_cell, x_label, y_label, sheet, save):
    eval_env = {"math": math, "pi": math.pi, "e": math.e}
    try:
        x_start = float(eval(str(start_val), eval_env))
        x_end = float(eval(str(end_val), eval_env))
    except Exception as e:
        click.secho(f"[Error] Invalid start/end expression: {e}", fg="red")
        return

    step = (x_end - x_start) / max(points - 1, 1)
    grid = [[x_label, y_label]]

    compiled_code = compile(expr, "<string>", "eval")
    for i in range(points):
        x = x_start + (i * step)
        eval_env['x'] = x
        try:
            y = float(eval(compiled_code, eval_env))
        except Exception as e:
            click.secho(f"[Error] Calculation failed at x={x}: {e}", fg="red")
            return
        grid.append([round(x, 4), round(y, 4)])

    controller.write_batch(start_cell, grid, sheet_name=sheet, save=save)
    end_row = points + 1
    click.secho(f"[Info] Generated range: {start_cell}:B{end_row} (Total {points} points)", fg="cyan")


@cli.command('chart', short_help="차트 생성 (기본: scatter-smooth)")
@click.argument('data_range')
@click.option('-s', '--sheet', help="시트명")
@click.option('--type', 'chart_type', default='scatter-smooth',
              help="scatter, scatter-smooth, scatter-line, line, column, bar, pie")
@click.option('--name', default='My Chart', help="차트 제목")
@click.option('--pos', help="차트 좌표 ('left,top')")
@click.option('--size', help="차트 크기 ('width,height')")
@click.option('-w', '--save', is_flag=True, help="생성 후 저장")
@click.pass_obj
def chart_cmd(controller, data_range, sheet, chart_type, name, pos, size, save):
    left, top = (120.0, 50.0)
    width, height = (450.0, 260.0)

    if pos:
        try:
            left, top = map(float, pos.split(','))
        except ValueError:
            click.secho("[Error] --pos는 'left,top' 형태여야 합니다.", fg="red")
            return
    if size:
        try:
            width, height = map(float, size.split(','))
        except ValueError:
            click.secho("[Error] --size는 'width,height' 형태여야 합니다.", fg="red")
            return

    controller.create_chart(data_range, chart_type=chart_type, title=name,
                            left=left, top=top, width=width, height=height,
                            sheet_name=sheet, save=save)


@cli.command('update-chart', short_help="차트 설정 및 타입 수정")
@click.argument('index', type=int)
@click.option('-s', '--sheet', help="시트명")
@click.option('--title', help="차트 제목")
@click.option('--type', 'chart_type', help="새 차트 타입 (scatter-smooth, scatter, line, column 등)")
@click.option('--pos', help="위치 ('left,top')")
@click.option('--size', help="크기 ('width,height')")
@click.option('-w', '--save', is_flag=True, help="수정 후 저장")
@click.pass_obj
def update_chart_cmd(controller, index, sheet, title, chart_type, pos, size, save):
    left, top = None, None
    width, height = None, None

    if pos:
        try:
            left, top = map(float, pos.split(','))
        except ValueError:
            click.secho("[Error] --pos는 'left,top' 형태여야 합니다.", fg="red")
            return
    if size:
        try:
            width, height = map(float, size.split(','))
        except ValueError:
            click.secho("[Error] --size는 'width,height' 형태여야 합니다.", fg="red")
            return

    controller.update_chart(index, title=title, chart_type=chart_type,
                            left=left, top=top, width=width, height=height,
                            sheet_name=sheet, save=save)


@cli.command('insert', short_help="단일 행 삽입")
@click.argument('row_idx', type=int)
@click.argument('data')
@click.option('-s', '--sheet', help="시트명")
@click.option('-w', '--save', is_flag=True, help="삽입 후 저장")
@click.pass_obj
def insert_cmd(controller, row_idx, data, sheet, save):
    controller.insert_row(row_idx, data, sheet_name=sheet, save=save)


@cli.command('clear', short_help="셀/영역 내용 삭제")
@click.argument('cell_ref')
@click.option('-s', '--sheet', help="시트명")
@click.option('-w', '--save', is_flag=True, help="삭제 후 저장")
@click.pass_obj
def clear_cmd(controller, cell_ref, sheet, save):
    controller.clear_content(cell_ref, sheet_name=sheet, save=save)


@cli.command('formula', short_help="수식 입력")
@click.argument('cell_ref')
@click.argument('formula_str')
@click.option('-s', '--sheet', help="시트명")
@click.option('-w', '--save', is_flag=True, help="수식 적용 후 저장")
@click.pass_obj
def formula_cmd(controller, cell_ref, formula_str, sheet, save):
    controller.set_formula(cell_ref, formula_str, sheet_name=sheet, save=save)


@cli.command('save', short_help="통합 문서 저장")
@click.pass_obj
def save_cmd(controller):
    controller.save()


if __name__ == '__main__':
    cli()
