import click
import win32com.client
import sys
import io

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def get_word_app():
    """Connect to the running MS Word application."""
    try:
        # Attempt to get the existing Word instance
        word_app = win32com.client.GetActiveObject("Word.Application")
        return word_app
    except Exception:
        # If no instance is running, this will fail
        return None

def parse_path(path_str):
    """Parse the path string like 'p:1' or 't:1,r:2,c:3'."""
    try:
        if path_str.startswith('p:'):
            return ('paragraph', int(path_str.split(':')[1]))
        elif path_str.startswith('t:'):
            # Format: t:1,r:2,c:3
            sub_parts = path_str[2:].split(',')
            t_idx = int(sub_parts[0])
            r_idx = int(sub_parts[1].replace('r:', ''))
            c_idx = int(sub_parts[2].replace('c:', ''))
            return ('table', t_idx, r_idx, c_idx)
    except Exception:
        raise click.BadParameter(f"Invalid path format: {path_str}. Use 'p:n' or 't:n,r:n,c:n'")
    return None

def get_color_rgb(color_name):
    """Map color name to RGB value."""
    color_map = {
        'black': 0,
        'white': 16777215,
        'red': 255,
        'green': 65280,
        'blue': 16711680,
        'yellow': 65535,
        'cyan': 16776960,
        'magenta': 16711935
    }
    return color_map.get(color_name.lower(), 16711680) # Default blue

@click.group(help="""
[USAGE PATTERNS]
1. List text content:
   python doc_live.py [--range START-END] list

2. Replace text:
   python doc_live.py [--range START-END] edit [TARGET] [NEW] [--color COLOR]

3. Add text:
   python doc_live.py add [TEXT] [--at PATH]

[ARGUMENT DETAILS]
- --range: Specify range (e.g., 'p:1' or 't:1,r:2,c:3')
- --color: black, white, red, green, blue, yellow, cyan, magenta

[EXAMPLES]
- python doc_live.py --range p:1 list
- python doc_live.py edit "Old" "New" --color red
- python doc_live.py add "Hello" --at p:1
""")
@click.option('--range', 'range_str', help="Specify range (e.g., 'p:1' or 't:1,r:2,c:3').")
@click.pass_context
def cli(ctx, range_str):
    """doc_live.py: A CLI tool to control the active MS Word document."""
    word_app = get_word_app()
    if not word_app:
        click.secho("Error: MS Word is not running or no document is open.", fg="red")
        ctx.exit(1)
    
    ctx.obj = {
        'app': word_app,
        'range_str': range_str
    }

@cli.command()
@click.pass_obj
def test_connection(obj):
    """Test the connection to the running MS Word application."""
    word_app = obj['app']
    try:
        doc_name = word_app.ActiveDocument.Name
        click.secho(f"Successfully connected! Active document: {doc_name}", fg="green")
    except Exception as e:
        click.secho(f"Connected to Word, but could not access ActiveDocument: {e}", fg="yellow")

@cli.command()
@click.option('--path', help="Target path (e.g., 'p:1' or 't:1,r:2,c:3')")
@click.pass_obj
def list(obj, path):
    """List the structure of the active document."""
    word_app = obj['app']
    
    try:
        doc = word_app.ActiveDocument
        click.echo(f"[Active Document: {doc.Name}]")
        
        if path:
            parsed = parse_path(path)
            if parsed[0] == 'paragraph':
                p_idx = parsed[1]
                if 1 <= p_idx <= doc.Paragraphs.Count:
                    text = doc.Paragraphs(p_idx).Range.Text.strip()
                    click.echo(f"[p:{p_idx}] {text}")
                else:
                    click.secho(f"Paragraph index {p_idx} out of range.", fg="yellow")
            elif parsed[0] == 'table':
                t_idx, r_idx, c_idx = parsed[1], parsed[2], parsed[3]
                if 1 <= t_idx <= doc.Tables.Count:
                    table = doc.Tables(t_idx)
                    if 1 <= r_idx <= table.Rows.Count and 1 <= c_idx <= table.Columns.Count:
                        cell_text = table.Cell(r_idx, c_idx).Range.Text.strip().replace('\r', '').replace('\x0b', '')
                        click.echo(f"[t:{t_idx}, r:{r_idx}, c:{c_idx}] {cell_text}")
                    else:
                        click.secho(f"Table cell index out of range.", fg="yellow")
                else:
                    click.secho(f"Table index {t_idx} out of range.", fg="yellow")
            return

        # Default: Full list
        for p_idx, para in enumerate(doc.Paragraphs, start=1):
            text = para.Range.Text.strip()
            if text:
                click.echo(f"[p:{p_idx}] {text}")

        for t_idx, table in enumerate(doc.Tables, start=1):
            click.echo(f"[t:{t_idx}]")
            for r_idx, row in enumerate(table.Rows, start=1):
                for c_idx, cell in enumerate(row.Cells, start=1):
                    cell_text = cell.Range.Text.strip().replace('\r', '').replace('\x0b', '')
                    if cell_text:
                        click.echo(f"  [r:{r_idx},c:{c_idx}] {cell_text}")
                        
    except Exception as e:
        click.secho(f"Error accessing document: {e}", fg="red")

@cli.command()
@click.argument('target')
@click.argument('new_text')
@click.option('--path', help="Target path (e.g., 'p:1' or 't:1,r:2,c:3')")
@click.option('--color', default='black', help="Color for the new text (black, white, red, green, blue, yellow, cyan, magenta).")
@click.pass_obj
def edit(obj, target, new_text, path, color):
    """Replace 'TARGET' with 'NEW' in the specified range or document."""
    word_app = obj['app']
    rgb_value = get_color_rgb(color)

    try:
        doc = word_app.ActiveDocument
        if path:
            parsed = parse_path(path)
            if parsed[0] == 'paragraph':
                p_idx = parsed[1]
                if 1 <= p_idx <= doc.Paragraphs.Count:
                    para_range = doc.Paragraphs(p_idx).Range
                    para_range.Text = new_text
                    para_range.Font.Color = rgb_value  # .RGB 대신 .Color 사용 시도
                    click.secho(f"Successfully updated paragraph {p_idx}.", fg="green")
                else:
                    click.secho(f"Paragraph index {p_idx} out of range.", fg="red")
            elif parsed[0] == 'table':
                t_idx, r_idx, c_idx = parsed[1], parsed[2], parsed[3]
                if 1 <= t_idx <= doc.Tables.Count:
                    table = doc.Tables(t_idx)
                    if 1 <= r_idx <= table.Rows.Count and 1 <= c_idx <= table.Columns.Count:
                        cell_range = table.Cell(r_idx, c_idx).Range
                        end_pos = cell_range.End - 1
                        cell_range.SetRange(cell_range.Start, end_pos)
                        cell_range.Text = new_text
                        cell_range.Font.Color = rgb_value # .RGB 대신 .Color 사용 시도
                        click.secho(f"Successfully updated table {t_idx}, cell [{r_idx}, {c_idx}].", fg="green")
                    else:
                        click.secho(f"Table cell index out of range.", fg="red")
                else:
                    click.secho(f"Table index {t_idx} out of range.", fg="red")
        else:
            # Global replace
            range_obj = doc.Content
            find_obj = range_obj.Find
            find_obj.ClearFormatting()
            find_obj.Replacement.ClearFormatting()
            
            # 1. 먼저 텍스트를 모두 교체 (ReplaceAll)
            find_obj.Execute(FindText=target, ReplaceWith=new_text, Replace=2) # 2 = wdReplaceAll
            
            # 2. 교체된 텍text를 다시 찾아 색상 적용
            search_range = doc.Content
            search_range.Find.ClearFormatting()
            
            found_count = 0
            # Find.Execute가 True를 반환할 동안 반복
            while search_range.Find.Execute(FindText=new_text):
                search_range.Font.Color = rgb_value
                search_range.Collapse(0) # wdCollapseEnd
                found_count += 1
                # 무한 루프 방지를 위해 검색 범위를 뒤로 밀어줌
                if search_range.End >= doc.Content.End:
                    break
            
            if found_count > 0:
                click.secho(f"Successfully replaced '{target}' with '{new_text}' and applied color '{color}' ({found_count} occurrences).", fg="green")
            else:
                click.secho(f"'{target}' not found or no changes made.", fg="yellow")
    except Exception as e:
        click.secho(f"Error during edit: {e}", fg="red")

@cli.command()
@click.argument('text')
@click.option('--at', help="Target position (e.g., 'p:1' or 't:1,r:2,c:3')")
@click.pass_obj
def add(obj, text, at):
    """Add TEXT to the specified position."""
    word_app = obj['app']

    try:
        doc = word_app.ActiveDocument
        if at:
            parsed = parse_path(at)
            if parsed[0] == 'paragraph':
                p_idx = parsed[1]
                if 1 <= p_idx <= doc.Paragraphs.Count:
                    para_range = doc.Paragraphs(p_idx).Range
                    para_range.Collapse(0) # 0 = wdCollapseEnd
                    para_range.InsertAfter(f"\n{text}")
                    click.secho(f"Added text after paragraph {p_idx}.", fg="green")
                else:
                    click.secho(f"Paragraph index {p_idx} out of range.", fg="red")
            elif parsed[0] == 'table':
                t_idx, r_idx, c_idx = parsed[1], parsed[2], parsed[3]
                if 1 <= t_idx <= doc.Tables.Count:
                    table = doc.Tables(t_idx)
                    if 1 <= r_idx <= table.Rows.Count and 1 <= c_idx <= table.Columns.Count:
                        cell_range = table.Cell(r_idx, c_idx).Range
                        end_pos = cell_range.End - 1
                        cell_range.SetRange(cell_range.Start, end_pos)
                        cell_range.InsertAfter(text)
                        click.secho(f"Added text to table {t_idx}, cell [{r_idx}, {c_idx}].", fg="green")
                    else:
                        click.secho(f"Table cell index out of range.", fg="red")
                else:
                    click.secho(f"Table index {t_idx} out of range.", fg="red")
        else:
            doc.Range(doc.Content.End - 1, doc.Content.End - 1).InsertAfter(f"\n{text}")
            click.secho("Added text at the end of the document.", fg="green")
    except Exception as e:
        click.secho(f"Error during add: {e}", fg="red")

if __name__ == "__main__":
    cli()
