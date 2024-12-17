from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import os

def create_labels(data, output_folder, file_name):
    # Initialize PDF
    pdf = canvas.Canvas(os.path.join(output_folder, file_name), pagesize=A4)
    width, height = A4

    # Grid settings (3x8)
    margin_x = .5 * cm
    margin_y = .5 * cm
    box_width = (width - 2 * margin_x) / 3
    box_height = (height - 2 * margin_y) / 8
    padding = 10  # Padding inside each box

    def draw_page(box_data):
        start_x = margin_x
        start_y = height - margin_y - box_height

        index = 0
        for row in range(8):  # 8 rows
            for col in range(3):  # 3 columns
                if index >= len(box_data):
                    return

                # Box position
                box_x = start_x + col * box_width
                box_y = start_y - row * box_height

                # Draw the box border
                # pdf.rect(box_x, box_y, box_width, box_height)

                # Extract entry
                name, address, zip_code, city = box_data[index]

                # Text positioning with vertical centering
                text_x = box_x + padding  # Horizontal padding
                text_y = box_y + box_height / 2 + 5  # Vertical center start

                # Add text
                pdf.setFont("Helvetica-Bold", 10)
                pdf.drawCentredString(box_x + box_width / 2, text_y + 10, name)  # Name centered
                adjusted_size = auto_adjust_font(pdf, max(box_data[index], key=len), box_width - 30, 8)
                pdf.setFont("Helvetica", adjusted_size)
                pdf.drawCentredString(box_x + box_width / 2, text_y, address)  # Address
                pdf.drawCentredString(box_x + box_width / 2, text_y - 10, f"{zip_code} {city}")  # ZIP & City

                index += 1

    # Paginate and draw all data
    box_per_page = 24  # 3x8 grid per page
    total_boxes = (len(data) + box_per_page - 1) // box_per_page

    for i in range(total_boxes):
        box_data = data[i * box_per_page: (i + 1) * box_per_page]
        draw_page(box_data)
        pdf.showPage()  # Add a new page

    # Save the PDF
    pdf.save()


def auto_adjust_font(pdf, text, box_width, max_font_size):
    font_size = max_font_size
    while pdf.stringWidth(text, "Helvetica", font_size) > box_width and font_size > 6:
        font_size -= 1
    return font_size