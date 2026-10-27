import sys
import io
import click
import win32com.client

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class PPTController:
    def __init__(self):
        self.ppt_app = None
        self.presentation = None
        self.start_page = 1
        self.end_page = 0

    def connect(self):
        try:
            self.ppt_app = win32com.client.GetActiveObject("PowerPoint.Application")
            self.presentation = self.ppt_app.ActivePresentation
            self.end_page = self.presentation.Slides.Count
            return True
        except Exception:
            return False

    def set_range(self, range_str):
        if not range_str:
            self.start_page = 1
            self.end_page = self.presentation.Slides.Count
            return

        try:
            if '-' in range_str:
                parts = range_str.split('-')
                self.start_page = int(parts[0])
                self.end_page = int(parts[1])
            else:
                self.start_page = int(range_str)
                self.end_page = int(range_str)

            total_slides = self.presentation.Slides.Count
            if self.start_page < 1: self.start_page = 1
            if self.end_page > total_slides: self.end_page = total_slides
            if self.start_page > self.end_page:
                raise ValueError("Start page cannot be greater than end page.")
        except ValueError as e:
            click.echo(f"[Error] Invalid range format: {e}", err=True)
            sys.exit(1)

    def list_text(self):
        if not self.presentation:
            click.echo("[Error] No active presentation found.", err=True)
            return

        click.echo(f"\n--- Document: {self.presentation.Name} (Range: {self.start_page}-{self.end_page}) ---")
        for i in range(self.start_page, self.end_page + 1):
            slide = self.presentation.Slides(i)
            click.echo(f"\n[Slide {i}]")
            found_any = False
            for shape in slide.Shapes:
                texts = self._get_text_recursive(shape)
                for t in texts:
                    click.echo(f"  > {t}")
                    found_any = True
            if not found_any:
                click.echo("  (No text found)")
        click.echo("\n" + "-"*40)

    def _get_text_recursive(self, shape):
        texts = []
        if shape.HasTextFrame:
            if shape.TextFrame.HasText:
                text = shape.TextFrame.TextRange.Text.strip()
                if text:
                    texts.append(text)
        if shape.Type == 6: # msoGroup
            for sub_shape in shape.GroupItems:
                texts.extend(self._get_text_recursive(sub_shape))
        return texts

    def _edit_recursive(self, shapes, target, new_text):
        count = 0
        for shape in shapes:
            if shape.HasTextFrame and shape.TextFrame.HasText:
                text_range = shape.TextFrame.TextRange
                if target in text_range.Text:
                    text_range.Replace(target, new_text)
                    count += 1
            if shape.Type == 6: # msoGroup
                count += self._edit_recursive(shape.GroupItems, target, new_text)
        return count

    def edit_text(self, target, new_text):
        if not self.presentation:
            click.echo("[Error] No active presentation found.", err=True)
            return
        count = 0
        for i in range(self.start_page, self.end_page + 1):
            slide = self.presentation.Slides(i)
            count += self._edit_recursive(slide.Shapes, target, new_text)
        click.echo(f"[Success] Updated {count} occurrence(s) in slides {self.start_page}-{self.end_page}.")

    def add_text(self, text, slide_index, left=0, top=0, width=300, height=50, font_size=18, color_name='blue'):
        if not self.presentation:
            click.echo("[Error] No active presentation found.", err=True)
            return

        # 색상 매핑
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
        rgb_value = color_map.get(color_name.lower(), 16711680) # 기본값 blue

        try:
            if slide_index < 1 or slide_index > self.presentation.Slides.Count:
                click.echo(f"[Error] Invalid slide index: {slide_index}", err=True)
                return

            slide = self.presentation.Slides(slide_index)
            shape = slide.Shapes.AddTextbox(1, left, top, width, height) 
            text_range = shape.TextFrame.TextRange
            text_range.Text = text
            text_range.Font.Size = font_size
            text_range.Font.Color.RGB = rgb_value
            
            click.echo(f"[Success] Added text to Slide {slide_index} at (x={left}, y={top}) with color '{color_name}'.")
        except Exception as e:
            click.echo(f"[Error] Failed to add text: {e}", err=True)

@click.group(help="""
[USAGE PATTERNS]
1. List text content:
   python ppt_live.py [--range START-END] list

2. Replace text:
   python ppt_live.py [--range START-END] edit [TARGET] [NEW]

3. Add text box:
   python ppt_live.py add [TEXT] [SLIDE_INDEX] [--left X] [--top Y] [--color COLOR]

[ARGUMENT DETAILS]
- --range: Slide range (e.g., '1-5' or '3')
- --left / --top: Integer coordinates (default: 0 / -30)
- --color: black, white, red, green, blue, yellow, cyan, magenta (default: blue)

[EXAMPLES]
- python ppt_live.py --range 1-3 list
- python ppt_live.py edit "Old" "New"
- python ppt_live.py add "Hello" 1 --left 100 --top 200 --color red
""")
@click.option('--range', 'range_str', help="Specify range (e.g., '1-5' or '3').")
@click.pass_context
def cli(ctx, range_str):
    """PowerPoint Automation Tool."""
    controller = PPTController()
    if not controller.connect():
        click.echo("[Error] PowerPoint is not running or no active document found.", err=True)
        ctx.exit(1)
    
    if range_str:
        controller.set_range(range_str)
    
    ctx.obj = controller

@cli.command(name='list')
@click.pass_obj
def list_command(controller):
    """List text content of slides (including Grouped items)."""
    controller.list_text()

@cli.command(name='edit')
@click.argument('target')
@click.argument('new_text')
@click.pass_obj
def edit_command(controller, target, new_text):
    """Replace 'TARGET' with 'NEW' in the specified range."""
    controller.edit_text(target, new_text)

@cli.command(name='add')
@click.argument('text')
@click.argument('slide_index', type=int)
@click.option('--left', default=0, type=int, help="X coordinate.")
@click.option('--top', default=-30, type=int, help="Y coordinate.")
@click.option('--color', default='blue', help="Color name (black, white, red, green, blue, yellow, cyan, magenta).")
@click.pass_obj
def add_command(controller, text, slide_index, left, top, color):
    """Add TEXT to the specified SLIDE."""
    controller.add_text(text, slide_index, left=left, top=top, color_name=color)

if __name__ == '__main__':
    cli()
