import io
import os

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import Color

A4_WIDTH = A4[0]
A4_HEIGHT = A4[1]

MIN_NAME_SIZE = 6


def register_font() -> str:
    """Built-in Helvetica can't draw Czech letters (ř, č, ě, ...), so use Arial when available."""
    path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf")
    if not os.path.exists(path):
        return "Helvetica"
    if "Arial" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Arial", path))
    return "Arial"

DEFAULT_FONT = register_font()


def to_color(value: str, fallback: Color = colors.lightgrey) -> Color:
    """Convert a CSS-like color string ("darkred", "#8b0000") to a reportlab Color."""
    try:
        return colors.toColor(value)
    except ValueError:
        return fallback


class PDFLabels:
    def __init__(
            self,
            rows:int = 16, columns:int = 4,
            name_offset = 10,
            name_size:float = 20,
            code_size:float = 20,
            stripe_width:float = 20,
            name_font:str = DEFAULT_FONT,
            file_name = "test.pdf",     # path or binary file-like object
            name_color: Color = colors.black,
            border_color:Color = colors.lightgrey
            ):

        self.name_size = name_size
        self.code_size = code_size
        self.name_font = name_font
        self.name_color = name_color
        self.stripe_width = stripe_width
        self.border_color = border_color


        self.name_offset = name_offset

        self.canvas = canvas.Canvas(file_name, pagesize=A4)

        self.rows = rows
        self.columns = columns

        self.row_height = A4_HEIGHT / self.rows
        self.column_width = A4_WIDTH / self.columns

        self.curr_row = 0
        self.curr_column = 0

        self.labels = []

    def add_label_border(self, x, y):
        self.canvas.setStrokeColor(self.border_color)
        self.canvas.rect(x, y, self.column_width, self.row_height, stroke=1, fill=0)

    def add_label_name(self, x, y, text):

        x += self.stripe_width + self.name_offset
        max_width = 4*20 - self.name_offset #TODO same offset as codes

        # shrink long names so they don't run into the codes
        size = self.name_size
        while size > MIN_NAME_SIZE and pdfmetrics.stringWidth(text, self.name_font, size) > max_width:
            size -= 0.5

        y = (y + self.row_height / 2) - (size / 2)

        self.canvas.setStrokeColor(self.name_color)
        self.canvas.setFillColor(self.name_color)
        self.canvas.setFont(self.name_font, size)
        self.canvas.drawString(x, y, text)

    def add_label_codes(self, x, y, codes:list[str]):
        x += self.stripe_width + self.name_offset + 4*20 #TODO
        y = (y + 0) + (self.code_size / 2)

        self.canvas.setStrokeColor(self.name_color)
        self.canvas.setFillColor(self.name_color)
        self.canvas.setFont(self.name_font, self.code_size)

        # first code on top
        for i, code in enumerate(reversed(codes)):
            self.canvas.drawString(x, y + i * self.code_size, code)

    def add_label_stripe(self, x, y, color:Color):
        self.canvas.setFillColor(color)
        self.canvas.rect(x, y, self.stripe_width, self.row_height, fill=1, stroke=0)

    def add_label(self, name: str, stripe_color: Color, codes: list[str] | None = None):

        # start a new page when the current one is full
        if self.curr_row >= self.rows:
            self.canvas.showPage()
            self.curr_row = 0

        # down left corner, filling the page from the top
        x = self.curr_column    * self.column_width
        y = A4_HEIGHT - (self.curr_row + 1) * self.row_height

        # stripe
        self.add_label_stripe(x, y, stripe_color)

        # border
        self.add_label_border(x, y)

        # name
        self.add_label_name(x, y, name)

        # codes
        self.add_label_codes(x, y, codes or [])

        #region row/col update
        self.curr_column += 1
        if self.curr_column >= self.columns:
            self.curr_column = 0
            self.curr_row += 1
        #endregion

    def save_to_file(self):
        self.canvas.save()


def delivery_labels_pdf(customer_orders) -> bytes:
    """One label per customer, from DBManager.orders_on(date) (list of CustomerOrdersDTO)."""
    buffer = io.BytesIO()
    doc = PDFLabels(rows=16, columns=4, name_size=12, code_size=12, file_name=buffer)

    for entry in customer_orders:
        codes = [f"{o.menu_item_code}: {o.count}" for o in entry.orders]
        doc.add_label(entry.customer.name, to_color(entry.customer.color), codes)

    doc.save_to_file()
    return buffer.getvalue()



def get_colors():
    with open("colors.txt", "r") as file:
        lines = file.readlines()

        colors = []
        for line in lines: colors.append(line.strip())

    return colors

def main():

    COLORS = get_colors()
    COLOR_NAMES = ["aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black", "blanchedalmond", "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse", "chocolate", "coral", "cornflower", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray", "darkgreen", "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange", "darkorchid", "darkred"]

    doc = PDFLabels(rows=16, columns=4, name_size=12, code_size=12)
    label_count = 62

    for i in range(label_count):

        color = getattr(colors, COLOR_NAMES[i % len(COLOR_NAMES)])
        doc.add_label(f"Burian{i}", color, ["P1: 0", "H2: 1", "H1: 1"])


    doc.save_to_file()


if __name__ == "__main__":
    main()




