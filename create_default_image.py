from PIL import Image, ImageDraw, ImageFont
import os

# Utwórz szary obraz
img = Image.new('RGB', (800, 600), color=(240, 240, 240))
draw = ImageDraw.Draw(img)

# Dodaj tekst "Brak zdjęcia"
try:
    # Próba użycia domyślnej czcionki
    font = ImageFont.truetype("arial.ttf", 40)
    draw.text((300, 280), "Brak zdjęcia", fill=(100, 100, 100), font=font)
except:
    # Alternatywne podejście, jeśli czcionka Arial nie jest dostępna
    draw.text((300, 280), "Brak zdjecia", fill=(100, 100, 100))

# Upewnij się, że katalog istnieje
os.makedirs('static/img', exist_ok=True)

# Zapisz obraz
img.save('static/img/default-recipe.jpg')

print("Domyślny obraz przepisu został utworzony w static/img/default-recipe.jpg") 