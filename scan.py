from PIL import Image
import io
import requests
import pytesseract

#pytesseract.pytesseract.tesseract_cmd = r"P:\Programs\Tesseract\tesseract.exe"
#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = ‘/app/.apt/usr/bin/tesseract’

def scan_image(photo):
    # Jer sliku dobivamo kao link, dohvacamo ju preko funkcije request()
    response = requests.get(photo)
    img = Image.open(io.BytesIO(response.content))

    text = pytesseract.image_to_string(img, lang='hrv+bos')
    
    print('Image scanned!\n')
    return(text)

if __name__ == "__main__":
    #path = 'https://raw.githubusercontent.com/mstjepan28/Test-files/master/20200323_142140.jpg?token=ANIL4UJ2NZNBT6QFSXKGXKS62YT5Q'
    path = r'https://firebasestorage.googleapis.com/v0/b/digitality-1234567890.appspot.com/o/undefined%2F1593238353041.png?alt=media&token=bba1496e-7dbc-4190-8526-05b81c5147a3'
    result = scan_image(path)
    print(result)