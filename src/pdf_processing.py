import os
import fitz
from tqdm import tqdm
from PIL import Image, ImageEnhance

def combine_images_to_pdf(image_paths, output_pdf_path):
    if not image_paths:
        return
    
    # If only one image, save it as a PDF directly
    if len(image_paths) == 1:
        img = Image.open(image_paths[0])
        img.convert("RGB").save(output_pdf_path)
        return

    # Open the images
    images = [Image.open(image) for image in image_paths]

    # Convert all images to RGB (some formats may be in different modes)
    images = [img.convert("RGB") for img in images]

    # Save images as a PDF
    images[0].save(output_pdf_path, save_all=True, append_images=images[1:])



def delete_images(directory_path):
    try:
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    except:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        pass

def pdf_to_images(pdf_path, output_folder, resolution, contrast_factor=3):
    delete_images(output_folder)
    print("\nGetting All Images From PDF...")
    doc = fitz.open(pdf_path)
    
    for i in tqdm(range(len(doc)), ncols=60, bar_format="{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}"):
        page = doc.load_page(i)
        # Get the image of the page
        image = page.get_pixmap(matrix=fitz.Matrix(resolution / 72, resolution / 72))
        image_path = f"{output_folder}/page-{i + 1}.png"
        
        # Convert to PIL Image to manipulate contrast
        pil_image = Image.frombytes("RGB", [image.width, image.height], image.samples)
        
        # Enhance the contrast of the image for better OCR
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced_image = enhancer.enhance(contrast_factor)
        
        # Save the enhanced image
        enhanced_image.save(image_path)
    
    doc.close()