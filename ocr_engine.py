import easyocr

reader = easyocr.Reader(['en'], gpu=True)

def extract_text(image_path):
    result = reader.readtext(image_path, detail=0)
    return "\n".join(result)