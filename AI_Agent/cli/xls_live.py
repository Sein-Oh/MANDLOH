import click
import win32com.client
import sys
import io

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class ExcelControllerFast:
    def __init__(self):
        self.app = None
        self.wb = None
        self.sheet = None

    def connect(self):
        """실행 중인 Excel 앱에 win32com으로 직접 연결"""
        try:
            self.app = win32com.client.GetActiveObject("Excel.Application")
            self.wb = self.app.ActiveWorkbook
            self.sheet = self.wb.ActiveSheet
            return True
        except Exception:
            return False

    def list_content(self, sheet_name=None):
        """시트의 데이터를 고속으로 읽어 출력"""
        try:
            target_sheet = self.wb.Worksheets(sheet_name) if sheet_name else self.sheet
            click.echo(f"\n--- Workbook: {self.wb.Name} | Sheet: {target_sheet.Name} ---")
            
            used_range = target_sheet.UsedRange
            start_row = used_range.Row
            start_col = used_range.Column
            end_row = start_row + used_range.Rows.Count - 1
            end_col = start_col + used_range.Columns.Count - 1

            data_range = target_sheet.Range(target_sheet.Cells(start_row, start_col), target_sheet.Cells(end_row, end_col))
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
            click.echo("-" * 40)
        except Exception as e:
            click.secho(f"[Error] {e}", fg="red")

    def edit_cell(self, cell_ref, new_value, color_name='black'):
        """특정 셀(예: 'A1' 또는 '6,4')의 값을 수정"""
        try:
            if ',' in cell_ref:
                try:
                    r, c = map(int, cell_ref.split(','))
                    target = self.sheet.Cells(r, c)
                except ValueError:
                    target = self.sheet.Range(cell_ref)
            else:
                target = self.sheet.Range(cell_ref)
                
            target.Value = new_value
            
            color_map = {
                'black': 0, 'white': 16777215, 'red': 255, 
                'green': 65280, 'blue': 16711680, 'yellow': 65535
            }
            target.Font.Color = color_map.get(color_name.lower(), 0)
            click.echo(f"[Success] Updated {cell_ref}")
        except Exception as e:
            click.secho(f"[Error] {e}", fg="red")

    def insert_row(self, row_idx, data):
        """지정된 행 위치에 새로운 행을 삽입하고 데이터를 입력"""
        try:
            self.sheet.Rows(row_idx).Insert()
            if isinstance(data, str):
                data_list = [d.strip() for d in data.split(',')]
            else:
                data_list = data
            
            for c_idx, val in enumerate(data_list, start=1):
                self.sheet.Cells(row_idx, c_idx).Value = val
            click.echo(f"[Success] Inserted row at {row_idx}")
        except Exception as e:
            click.secho(f"[Error] Failed to insert row: {e}", fg="red")

    def clear_content(self, cell_ref):
        """특정 셀 또는 영역의 내용을 지움"""
        try:
            if ',' in cell_ref:
                try:
                    r, c = map(int, cell_ref.split(','))
                    target = self.sheet.Cells(r, c)
                except ValueError:
                    target = self.sheet.Range(cell_ref)
            else:
                target = self.sheet.Range(cell_ref)
            
            target.ClearContents()
            click.echo(f"[Success] Cleared content in {cell_ref}")
        except Exception as e:
            click.secho(f"[Error] Failed to clear: {e}", fg="red")

    def set_formula(self, cell_ref, formula):
        """특정 셀에 수식 입력 (예: 'A1' '=SUM(A1:A10)')"""
        try:
            if ',' in cell_ref:
                try:
                    r, c = map(int, cell_ref.split(','))
                    target = self.sheet.Cells(r, c)
                except ValueError:
                    target = self.sheet.Range(cell_ref)
            else:
                target = self.sheet.Range(cell_ref)
            
            if not formula.startswith('='):
                formula = '=' + formula
                
            target.Formula = formula
            click.echo(f"[Success] Set formula in {cell_ref}: {formula}")
        except Exception as e:
            click.secho(f"[Error] Failed to set formula: {e}", fg="red")

    def create_chart(self, data_range_str, chart_type='column', title='My Chart', left=100, top=100, width=375, height=225):
        """지정된 범위의 데이터를 바탕로 차트 생성"""
        try:
            type_map = {'column': 51, 'line': 4, 'pie': 57, 'scatter': 79}
            xl_type = type_map.get(chart_type.lower(), 51)
            data_range = self.sheet.Range(data_range_str)
            
            chart_obj = self.sheet.ChartObjects().Add(left, top, width, height)
            chart = chart_obj.Chart
            chart.SetSourceData(Source=data_range)
            chart.ChartType = xl_type
            chart.HasTitle = True
            chart.ChartTitle.Text = title
            click.echo(f"[Success] Created {chart_type} chart for range {data_range_str}")
        except Exception as e:
            click.secho(f"[Error] Failed to create chart: {e}", fg="red")

    def update_chart(self, index, title=None, chart_type=None, left=None, top=None, width=None, height=None):
        """기존 차트 수정 (index는 0부터 시작)"""
        try:
            chart_obj = self.sheet.ChartObjects(index + 1)
            chart = chart_obj.Chart
            
            if title:
                chart.HasTitle = True
                chart.ChartTitle.Text = title
                click.echo(f"Updated title to: {title}")
                
            if chart_type:
                type_map = {
                    'column': 51,
                    'line': 4,
                    'pie': 57,
                    'scatter': 79
                }
                xl_type = type_map.get(chart_type.lower())
                if xl_type:
                    chart.ChartType = xl_type
                    click.echo(f"Updated type to: {chart_type} (Value: {xl_type})")
                else:
                    click.secho(f"[Error] Unknown chart type: {chart_type}", fg="red")
                
            if left is not None and top is not None:
                chart_obj.Left = left
                chart_obj.Top = top
                click.echo(f"Updated position to: {left}, {top}")
                
            if width is not None and height is not None:
                chart_obj.Width = width
                chart_obj.Height = height
                click.echo(f"Updated size to: {width}x{height}")
                
            click.echo(f"[Success] Updated chart #{index}")
        except Exception as e:
            click.secho(f"[Error] Failed to update chart: {e}", fg="red")

@click.group()
@click.pass_context
def cli(ctx):
    controller = ExcelControllerFast()
    if not controller.connect():
        click.secho("Error: Excel is not running.", fg="red")
        ctx.exit(1)
    ctx.obj = controller

@cli.command()
@click.option('--sheet', help="Sheet name")
@click.pass_obj
def list(controller, sheet):
    controller.list_content(sheet)

@cli.command()
@click.argument('cell_ref')
@click.argument('new_value')
@click.option('--color', default='black')
@click.pass_obj
def edit(controller, cell_ref, new_value, color):
    controller.edit_cell(cell_ref, new_value, color)

@cli.command()
@click.argument('row_idx', type=int)
@click.argument('data')
@click.pass_obj
def insert(controller, row_idx, data):
    controller.insert_row(row_idx, data)

@cli.command()
@click.argument('cell_ref')
@click.pass_obj
def clear(controller, cell_ref):
    controller.clear_content(cell_ref)

@cli.command()
@click.argument('cell_ref')
@click.argument('formula')
@click.pass_obj
def formula(controller, cell_ref, formula):
    controller.set_formula(cell_ref, formula)

@cli.command()
@click.argument('data_range')
@click.option('--type', 'chart_type', default='column', help="column, line, pie, scatter")
@click.option('--name', default='My Chart', help="Chart title")
@click.option('--left', default=100, help="X position")
@click.option('--top', default=100, help="Y position")
@click.option('--width', default=375, help="Width")
@click.option('--height', default=225, help="Height")
@click.pass_obj
def chart(controller, data_range, chart_type, name, left, top, width, height):
    controller.create_chart(data_range, chart_type, name, left, top, width, height)

@cli.command()
@click.argument('index', type=int)
@click.option('--title', help="New chart title")
@click.option('--type', 'chart_type', help="New chart type (column, line, pie, scatter)")
@click.option('--pos', help="New position (format: left,top)")
@click.option('--size', help="New size (format: width,height)")
@click.pass_obj
def update_chart(controller, index, title, chart_type, pos, size):
    """Update an existing chart. index: 0-based index of the chart."""
    left, top = None, None
    width, height = None, None
    
    if pos:
        try:
            left, top = map(float, pos.split(','))
        except ValueError:
            click.secho("[Error] Position must be 'left,top'", fg="red")
            return
            
    if size:
        try:
            width, height = map(float, size.split(','))
        except ValueError:
            click.secho("[Error] Size must be 'width,height'", fg="red")
            return

    controller.update_chart(index, title, chart_type, left, top, width, height)

if __name__ == '__main__':
    cli()
