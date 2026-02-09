import re
from PIL import Image, ImageDraw

def render_gcode(input_file, output_file, image_width=800, image_height=600, margin=20):
    # 1. Wczytanie i parsowanie G-code
    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku {input_file}")
        return

    # Zmienne stanu
    pen_down = False
    current_x, current_y = 0.0, 0.0
    
    # Lista odcinków do narysowania: [(x1, y1, x2, y2), ...]
    segments = []
    
    # Zmienne do obliczenia skali (min/max)
    min_x, max_x = float('inf'), float('-inf')
    min_y, max_y = float('inf'), float('-inf')

    # Regex do wyciągania liczb po X i Y
    coord_pattern = re.compile(r'([XY])(-?\d*\.?\d+)')

    print("Analiza G-code...")
    
    for line in lines:
        line = line.strip().upper()
        
        # Obsługa stanu pisaka
        if 'M3' in line:
            pen_down = True
        elif 'M5' in line:
            pen_down = False
        
        # Sprawdzamy czy linia zawiera ruch (G0 lub G1)
        if 'G0' in line or 'G1' in line:
            # Szukamy X i Y w linii
            found_coords = dict(re.findall(r'([XY])(-?\d*\.?\d+)', line))
            
            new_x = float(found_coords['X']) if 'X' in found_coords else current_x
            new_y = float(found_coords['Y']) if 'Y' in found_coords else current_y
            
            # Jeśli pisak jest w dole, zapisujemy odcinek
            if pen_down:
                segments.append((current_x, current_y, new_x, new_y))
                
                # Aktualizacja zakresów do skalowania
                min_x, max_x = min(min_x, current_x, new_x), max(max_x, current_x, new_x)
                min_y, max_y = min(min_y, current_y, new_y), max(max_y, current_y, new_y)
            
            # Aktualizacja pozycji głowicy (nawet jak pisak w górze)
            current_x, current_y = new_x, new_y

    if not segments:
        print("Nie znaleziono żadnych ruchów rysujących (z opuszczonym pisakiem M3)!")
        return

    print(f"Znaleziono {len(segments)} odcinków.")
    print(f"Obszar roboczy: X[{min_x:.2f}, {max_x:.2f}] Y[{min_y:.2f}, {max_y:.2f}]")

    # 2. Obliczanie skali, aby zmieścić rysunek w oknie
    data_width = max_x - min_x
    data_height = max_y - min_y
    
    # Zabezpieczenie przed dzieleniem przez zero (gdy rysunek to kropka lub linia prosta)
    if data_width == 0: data_width = 1
    if data_height == 0: data_height = 1

    scale_x = (image_width - 2 * margin) / data_width
    scale_y = (image_height - 2 * margin) / data_height
    scale = min(scale_x, scale_y) # Zachowaj proporcje (aspect ratio)

    # Funkcja pomocnicza do transformacji współrzędnych
    def transform(x, y):
        # Przesuwamy do 0,0 (odejmując min)
        # Skalujemy
        # Dodajemy margines
        tx = (x - min_x) * scale + margin
        
        # Dla Y musimy odwrócić oś (bo w obrazkach 0 jest na górze, a w CNC na dole)
        # Obliczamy wysokość rysunku w pikselach i odejmujemy od dołu obrazka
        ty = image_height - margin - ((y - min_y) * scale)
        return tx, ty

    # 3. Rysowanie
    img = Image.new('RGB', (image_width, image_height), 'white')
    draw = ImageDraw.Draw(img)

    for x1, y1, x2, y2 in segments:
        px1, py1 = transform(x1, y1)
        px2, py2 = transform(x2, y2)
        # Rysujemy czarną linię o grubości 2px
        draw.line((px1, py1, px2, py2), fill='black', width=2)

    # 4. Zapis
    img.save(output_file)
    print(f"Sukces! Obraz zapisano jako: {output_file}")

# --- Użycie ---
# Podmień 'drawing.gcode' na nazwę swojego pliku, jeśli jest inna
render_gcode('drawing.gcode', 'wyjscie.png')
