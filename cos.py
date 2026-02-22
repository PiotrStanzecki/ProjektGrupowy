import sys
import os
from PIL import Image, ImageDraw

def gcode_to_image(input_file, output_file="output.png", width=900, height=400):
    """
    Parses a G-code file and renders it to a PNG image.
    """
    
    # 1. Read the G-code file
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        return

    with open(input_file, 'r') as f:
        lines = f.readlines()

    # 2. Setup the Canvas
    im = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(im)

    # 3. Parser State
    pen_down = False
    current_x = 0.0
    current_y = 0.0
    
   
    color_map = {
        'C0': 'black',
        'C1': 'red',
        'C2': 'blue',
        'C3': 'green'
    }
    current_color = 'black'

    
    scale_x = width / 150.0  
    scale_y = height / 40.0

    print(f"Rendering {input_file}...")

    for line in lines:
        line = line.strip().upper()
        if not line: continue

        
        if line in color_map:
            current_color = color_map[line]
        
        
        elif line == "M3":
            pen_down = True
        elif line == "M5":
            pen_down = False
            
        # --- Handle Movement ---
        elif line.startswith("G01") or line.startswith("G1"):
            # Parse target coordinates
            parts = line.split()
            target_x = current_x
            target_y = current_y
            
            for part in parts:
                if part.startswith('X'):
                    target_x = float(part[1:])
                if part.startswith('Y'):
                    target_y = float(part[1:])
            
            # If the pen is down, draw a line from old pos to new pos
            if pen_down:
            
                
                # Start point
                start_px_x = width - (current_x * scale_x)
                start_px_y = current_y * scale_y
                
                # End point
                end_px_x = width - (target_x * scale_x)
                end_px_y = target_y * scale_y

                draw.line(
                    [(start_px_x, start_px_y), (end_px_x, end_px_y)], 
                    fill=current_color, 
                    width=3
                )

            # Update position
            current_x = target_x
            current_y = target_y

    # 5. Save output
    im.save(output_file)
    print(f"Done! Image saved to {output_file}")

if __name__ == "__main__":
    #
    if len(sys.argv) < 2:
        print("Usage: python gcode_to_png.py <gcode_file> [output_file]")
        print("Example: python gcode_to_png.py drawing1.gcode")
    else:
        gcode_path = sys.argv[1]
        out_path = sys.argv[2] if len(sys.argv) > 2 else "output.png"
        gcode_to_image(gcode_path, out_path)

#python cos.py drawing1.gcode