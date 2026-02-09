import customtkinter as ctk
from tkinter import ALL
from PIL import Image, ImageDraw
from math import hypot
import numpy as np

# Ustawienia stałe
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 400
TARGET_WIDTH = 150
TARGET_HEIGHT = 40 

# Konfiguracja wyglądu
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PathGcodeGenerator:
    def __init__(self, paths, output_file, canvas_size, target_size): 
        self.paths = paths
        self.output_file = output_file
        self.tolerance = 1.5
        canvas_w = canvas_size[0]

        # Transformacja współrzędnych
        self.paths = [[(canvas_w - x, y) for x, y in path] for path in paths]
        self.paths = [t for t in self.paths if all(val >= 0 for coord in t for val in coord)]
        
        self.sx = target_size[0] / canvas_size[0]
        self.sy = target_size[1] / canvas_size[1]

    def dist(self, p1, p2):
        return hypot(p1[0] - p2[0], p1[1] - p2[1])

    def fmt(self, val, step):
        return f"{val:.2f}".rstrip('0').rstrip('.')

    def generate(self):
        try:
            scaled_polylines = []
            for path in self.paths:
                if len(path) < 2: continue
                scaled_path = [(p[0] * self.sx, p[1] * self.sy) for p in path]
                scaled_polylines.append(scaled_path)

            if not scaled_polylines:
                return False, "Brak ścieżek."

            ordered_paths = []
            cx, cy = 0.0, 0.0 
            pool = scaled_polylines[:] 
            
            while pool:
                best_idx = -1
                best_dist = float('inf')
                reverse_needed = False
                for i, path in enumerate(pool):
                    d_start = self.dist((cx, cy), path[0])
                    d_end = self.dist((cx, cy), path[-1])
                    if d_start < best_dist:
                        best_dist = d_start; best_idx = i; reverse_needed = False
                    if d_end < best_dist:
                        best_dist = d_end; best_idx = i; reverse_needed = True
                
                chosen = pool.pop(best_idx)
                if reverse_needed: chosen = chosen[::-1]
                ordered_paths.append(chosen)
                cx, cy = chosen[-1]

            g = ['M5']
            pen_is_down = False
            last_x, last_y = -100000.0, -100000.0

            for path in ordered_paths:
                start_pt = path[0]
                if self.dist((last_x, last_y), start_pt) > self.tolerance:
                    if pen_is_down:
                        g.append("M5"); pen_is_down = False
                    g.append(f"G01 X{self.fmt(start_pt[0], 0.023)} Y{self.fmt(start_pt[1], 0.043)}")
                    last_x, last_y = start_pt
                
                if not pen_is_down:
                    g.append("M3"); pen_is_down = True
                
                for pt in path[1:]:
                    if self.dist((last_x, last_y), pt) > 0.005:
                        g.append(f"G01 X{self.fmt(pt[0], 0.01)} Y{self.fmt(pt[1], 0.01)}")
                        last_x, last_y = pt

            g.extend(["M5", "M2"])
            with open(self.output_file, 'w') as f:
                f.write('\n'.join(g))
            return True, len(g)
        except Exception as e:
            return False, str(e)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Modern G-Code Paint")
        self.geometry("800x700")
        self.resizable(False, False)

        # Zmienne stanu
        self.colorFg = 'black'
        self.penWidth = 5
        self.oldX = None
        self.oldY = None
        self.all_paths = []
        self.current_path = []
        self.line_start_x = None
        self.line_start_y = None
        self.current_line_id = None

        # Obraz do zapisu
        self.image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.image)

        self.setup_ui()
        self.enablePenTool()

    def setup_ui(self):
        # Panel boczny (Sidebar)
        self.sidebar = ctk.CTkFrame(self, width=150, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="Narzędzia", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=20)

        # Przyciski kolorów
        ctk.CTkButton(self.sidebar, text="Czerwony", fg_color="red", hover_color="#cc0000", 
                      command=lambda: self.changeColor('red')).pack(pady=5, padx=10)
        ctk.CTkButton(self.sidebar, text="Niebieski", fg_color="blue", hover_color="#0000cc", 
                      command=lambda: self.changeColor('blue')).pack(pady=5, padx=10)
        ctk.CTkButton(self.sidebar, text="Czarny", fg_color="#222222", 
                      command=lambda: self.changeColor('black')).pack(pady=5, padx=10)

        # Przełącznik linii
        self.checkvar = ctk.BooleanVar(value=False)
        self.line_switch = ctk.CTkSwitch(self.sidebar, text="Tryb Linii", variable=self.checkvar, 
                                         command=self.toggle_mode)
        self.line_switch.pack(pady=15)

        # Suwak promienia koła
        self.radius_label = ctk.CTkLabel(self.sidebar, text="Promień koła:")
        self.radius_label.pack()
        self.radius_slider = ctk.CTkSlider(self.sidebar, from_=5, to=50, number_of_steps=45)
        self.radius_slider.pack(pady=5, padx=10)

        ctk.CTkButton(self.sidebar, text="Tryb Koła", command=self.enableCircleTool).pack(pady=5, padx=10)

        # Przyciski akcji
        self.btn_gcode = ctk.CTkButton(self.sidebar, text="GENERUJ G-CODE", fg_color="#28a745", 
                                       hover_color="#218838", command=self.createGCode)
        self.btn_gcode.pack(side="bottom", pady=10, padx=10)

        self.btn_clear = ctk.CTkButton(self.sidebar, text="Wyczyść", fg_color="#dc3545", 
                                       hover_color="#c82333", command=self.clearCanv)
        self.btn_clear.pack(side="bottom", pady=5, padx=10)

        # Obszar rysowania (Canvas musi pozostać standardowy z tkinter, bo ctk nie ma własnego Canvas)
        self.c = ctk.CTkCanvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white", highlightthickness=0)
        self.c.pack(side="right", padx=20, pady=20)

    def toggle_mode(self):
        if self.checkvar.get():
            self.enableLineTool()
        else:
            self.enablePenTool()

    def enablePenTool(self):
        self.c.unbind('<Button-1>')
        self.c.bind('<B1-Motion>', self.paint)
        self.c.bind('<ButtonRelease-1>', self.reset)

    def paint(self, e):
        if self.oldX and self.oldY:
            self.c.create_line(self.oldX, self.oldY, e.x, e.y, width=self.penWidth, 
                               fill=self.colorFg, capstyle='round', smooth=True)
            self.draw.line([self.oldX, self.oldY, e.x, e.y], fill=self.colorFg, width=self.penWidth)
        self.oldX, self.oldY = e.x, e.y
        self.current_path.append((e.x, e.y))

    def reset(self, e):
        self.oldX = self.oldY = None
        if len(self.current_path) > 1:
            self.all_paths.append(self.current_path)
        self.current_path = []

    def enableLineTool(self):
        self.c.unbind('<B1-Motion>')
        self.c.bind('<Button-1>', self.startLine)
        self.c.bind('<B1-Motion>', self.dragLine)
        self.c.bind('<ButtonRelease-1>', self.endLine)

    def startLine(self, e):
        self.line_start_x, self.line_start_y = e.x, e.y
        self.current_line_id = self.c.create_line(e.x, e.y, e.x, e.y, fill=self.colorFg, width=self.penWidth)

    def dragLine(self, e):
        if self.current_line_id:
            self.c.coords(self.current_line_id, self.line_start_x, self.line_start_y, e.x, e.y)

    def endLine(self, e):
        if self.current_line_id:
            self.draw.line([self.line_start_x, self.line_start_y, e.x, e.y], fill=self.colorFg, width=self.penWidth)
            self.all_paths.append([(self.line_start_x, self.line_start_y), (e.x, e.y)])
            self.current_line_id = None

    def enableCircleTool(self):
        self.c.unbind('<B1-Motion>')
        self.c.bind('<Button-1>', self.drawCircleAt)

    def drawCircleAt(self, e):
        R = self.radius_slider.get()
        points = []
        N = 60 # Dokładność koła
        for i in range(N + 1):
            angle = 2 * np.pi * i / N
            px = e.x + R * np.cos(angle)
            py = e.y + R * np.sin(angle)
            points.append((px, py))
        
        # Rysowanie na canvasie
        for i in range(1, len(points)):
            self.c.create_line(points[i-1][0], points[i-1][1], points[i][0], points[i][1], 
                               fill=self.colorFg, width=self.penWidth)
            self.draw.line([points[i-1], points[i]], fill=self.colorFg, width=self.penWidth)
        
        self.all_paths.append(points)
        self.enablePenTool() # Powrót do pędzla po narysowaniu koła

    def clearCanv(self):
        self.c.delete(ALL)
        self.draw.rectangle([0, 0, CANVAS_WIDTH, CANVAS_HEIGHT], fill="white")
        self.all_paths = []

    def changeColor(self, color):
        self.colorFg = color

    def createGCode(self):
        generator = PathGcodeGenerator(self.all_paths, "drawing.gcode", 
                                      (CANVAS_WIDTH, CANVAS_HEIGHT), (TARGET_WIDTH, TARGET_HEIGHT))
        success, info = generator.generate()
        if success:
            print(f"Sukces: Zapisano {info} linii.")
        else:
            print(f"Błąd: {info}")

if __name__ == "__main__":
    app = App()
    app.mainloop()