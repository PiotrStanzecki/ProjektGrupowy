import customtkinter as ctk
from tkinter import ALL
from PIL import Image, ImageDraw
from math import hypot
import numpy as np
import os

CANVAS_WIDTH = 900
CANVAS_HEIGHT = 400
TARGET_WIDTH = 150
TARGET_HEIGHT = 40 

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class PathGcodeGenerator:
    def __init__(self, paths, output_file, canvas_size, target_size): 
        self.output_file = output_file
        self.tolerance = 1.5
        canvas_w = canvas_size[0]
        
        transformed = [[(canvas_w - x, y) for x, y in path] for path in paths]
        self.paths = [t for t in transformed if all(val >= 0 for coord in t for val in coord)]
        self.sx = target_size[0] / canvas_size[0]
        self.sy = target_size[1] / canvas_size[1]

    def dist(self, p1, p2):
        return hypot(p1[0] - p2[0], p1[1] - p2[1])

    def fmt(self, val):
        return f"{val:.2f}".rstrip('0').rstrip('.')

    def generate(self):
        try:
            scaled_polylines = []
            for path in self.paths:
                if len(path) < 2: continue
                scaled_path = [(p[0] * self.sx, p[1] * self.sy) for p in path]
                scaled_polylines.append(scaled_path)
            
            if not scaled_polylines: return False, "Empty"

            
            ordered_paths = []
            cx, cy = 0.0, 0.0 
            pool = scaled_polylines[:] 
            while pool:
                best_idx, best_dist, reverse_needed = -1, float('inf'), False
                for i, path in enumerate(pool):
                    d_start, d_end = self.dist((cx, cy), path[0]), self.dist((cx, cy), path[-1])
                    if d_start < best_dist:
                        best_dist, best_idx, reverse_needed = d_start, i, False
                    if d_end < best_dist:
                        best_dist, best_idx, reverse_needed = d_end, i, True
                chosen = pool.pop(best_idx)
                if reverse_needed: chosen = chosen[::-1]
                ordered_paths.append(chosen)
                cx, cy = chosen[-1]

            g = []
            pen_is_down = False
            last_x, last_y = -100000.0, -100000.0
            
            for path in ordered_paths:
                if self.dist((last_x, last_y), path[0]) > self.tolerance:
                    if pen_is_down: 
                        g.append("M5")
                        pen_is_down = False
                    g.append(f"G01 X{self.fmt(path[0][0])} Y{self.fmt(path[0][1])}")
                    last_x, last_y = path[0]
                
                if not pen_is_down: 
                    g.append("M3")
                    pen_is_down = True
                
                for pt in path[1:]:
                    if self.dist((last_x, last_y), pt) > 0.01:
                        g.append(f"G01 X{self.fmt(pt[0])} Y{self.fmt(pt[1])}")
                        last_x, last_y = pt
            
            g.append("M5")
            with open(self.output_file, 'w') as f: f.write('\n'.join(g))
            return True, len(g)
        except Exception as e: return False, str(e)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("G-Code Paint")
        self.geometry("1000x700")
        
        self.color_commands = {
            'black': 'C0',
            'red': 'C1',
            'blue': 'C2',
            'green': 'C3'
        }
        
        self.all_paths = {color: [] for color in self.color_commands.keys()}
        self.colorFg, self.penWidth, self.current_path = 'black', 5, []
        self.oldX = self.oldY = self.line_start_x = self.line_start_y = self.current_line_id = None
        
        self.image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.image)
        
        self.setup_ui()
        self.enablePenTool()

    def setup_ui(self):
        self.sidebar = ctk.CTkFrame(self, width=200); self.sidebar.pack(side="left", fill="y")
        ctk.CTkLabel(self.sidebar, text="Tools", font=("Arial", 18, "bold")).pack(pady=10)
        
        for col in self.color_commands.keys():
            btn_txt = f"{col.capitalize()}"
            ctk.CTkButton(self.sidebar, text=btn_txt, fg_color=col if col!='black' else "#222", 
                          command=lambda c=col: self.changeColor(c)).pack(pady=5, padx=20)
        
        #Line tool
        self.checkvar = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.sidebar, text="Line tool", variable=self.checkvar, command=self.toggle_mode).pack(pady=10)

        #Square tool
        self.square_slider = ctk.CTkSlider(self.sidebar, from_=5, to=100); self.square_slider.pack(pady=5)
        ctk.CTkButton(self.sidebar, text="Square tool", command=self.enableSquareTool).pack(pady=5)
        
        #Circle tool
        self.radius_slider = ctk.CTkSlider(self.sidebar, from_=5, to=100); self.radius_slider.pack(pady=5)
        ctk.CTkButton(self.sidebar, text="Circle tool", command=self.enableCircleTool).pack(pady=5)

        #Star tool
        self.star_slider = ctk.CTkSlider(self.sidebar, from_=5, to=100); self.star_slider.pack(pady=5)
        ctk.CTkButton(self.sidebar, text="Star tool", command=self.enableStarTool).pack(pady=5)
        
        ctk.CTkButton(self.sidebar, text="GENERATE G-CODE", fg_color="#28a745", command=self.createGCode).pack(side="bottom", pady=20)
        ctk.CTkButton(self.sidebar, text="CLEAR CANVAS", fg_color="#dc3545", command=self.clearCanv).pack(side="bottom", pady=5)
        
        self.c = ctk.CTkCanvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white"); self.c.pack(side="right", padx=20)

    def changeColor(self, color): self.colorFg = color
    def toggle_mode(self): self.enableLineTool() if self.checkvar.get() else self.enablePenTool()
    def toggle_mode2(self): self.enableSquareTool() if self.checkvar.get() else self.enablePenTool()
    def enablePenTool(self): self.c.unbind('<Button-1>'); self.c.bind('<B1-Motion>', self.paint); self.c.bind('<ButtonRelease-1>', self.reset)
    
    def paint(self, e):
        if self.oldX and self.oldY:
            self.c.create_line(self.oldX, self.oldY, e.x, e.y, width=self.penWidth, fill=self.colorFg, capstyle='round')
            self.draw.line([self.oldX, self.oldY, e.x, e.y], fill=self.colorFg, width=self.penWidth)
        self.oldX, self.oldY = e.x, e.y
        self.current_path.append((e.x, e.y))

    def reset(self, e):
        self.oldX = self.oldY = None
        if len(self.current_path) > 1: self.all_paths[self.colorFg].append(self.current_path)
        self.current_path = []

    def enableLineTool(self): 
        self.c.bind('<Button-1>', self.startLine)
        self.c.bind('<B1-Motion>', self.dragLine)
        self.c.bind('<ButtonRelease-1>', self.endLine)

    def enableStarTool(self): 
        self.c.unbind('<B1-Motion>') 
        self.c.bind('<Button-1>', self.drawStar)

    def enableSquareTool(self): 
        self.c.unbind('<B1-Motion>')
        self.c.bind('<Button-1>', self.drawSquare)

    def startLine(self, e):
        self.line_start_x, self.line_start_y = e.x, e.y
        self.current_line_id = self.c.create_line(e.x, e.y, e.x, e.y, fill=self.colorFg, width=self.penWidth)

    def dragLine(self, e):
        if self.current_line_id: self.c.coords(self.current_line_id, self.line_start_x, self.line_start_y, e.x, e.y)

    def endLine(self, e):
        if self.current_line_id:
            self.draw.line([self.line_start_x, self.line_start_y, e.x, e.y], fill=self.colorFg, width=self.penWidth)
            self.all_paths[self.colorFg].append([(self.line_start_x, self.line_start_y), (e.x, e.y)])
            self.current_line_id = None

    def enableCircleTool(self): 
        self.c.unbind('<B1-Motion>'); 
        self.c.bind('<Button-1>', self.drawCircleAt)


    def drawStar(self, e):
        #R is the outer radius 
        R = self.star_slider.get() 
        # r is the inner radius (where the arms meet)
        r = 0.5 * R  
        pts = []

        # We need 11 points: 5 outer + 5 inner + 1 to close the loop
        for i in range(11):
            # Calculate angle: start at -90 deg (top), increment by 36 deg (pi/5)
            alpha = i * (np.pi / 5) - (np.pi / 2)
            
            # Even indices are outer points, odd indices are inner points
            current_radius = R if i % 2 == 0 else r
            
            px = e.x + current_radius * np.cos(alpha)
            py = e.y + current_radius * np.sin(alpha)
            pts.append((px, py))

        # Draw the lines connecting the points
        for i in range(1, len(pts)):
            self.c.create_line(pts[i-1], pts[i], fill=self.colorFg, width=self.penWidth)
            self.draw.line([pts[i-1], pts[i]], fill=self.colorFg, width=self.penWidth)
            
        self.all_paths[self.colorFg].append(pts)
        self.enablePenTool()

    def drawSquare(self, e):
        R, pts = self.square_slider.get(), []

        pts.append((e.x - R, e.y + R))
        pts.append((e.x + R, e.y + R))
        pts.append((e.x + R, e.y - R))
        pts.append((e.x - R, e.y - R))
        pts.append((e.x - R, e.y + R))

        for i in range(1, len(pts)):
            self.c.create_line(pts[i-1], pts[i], fill=self.colorFg, width=self.penWidth)
            self.draw.line([pts[i-1], pts[i]], fill=self.colorFg, width=self.penWidth)
        self.all_paths[self.colorFg].append(pts)
        self.enablePenTool()
        
    def drawCircleAt(self, e):
        R, pts = self.radius_slider.get(), []
        N = 60
        for i in range(N + 1):
            a = 2 * np.pi * i / N
            pts.append((e.x + R * np.cos(a), e.y + R * np.sin(a)))
        for i in range(1, len(pts)):
            self.c.create_line(pts[i-1], pts[i], fill=self.colorFg, width=self.penWidth)
            self.draw.line([pts[i-1], pts[i]], fill=self.colorFg, width=self.penWidth)
        self.all_paths[self.colorFg].append(pts)
        self.enablePenTool()

    def clearCanv(self):
        self.c.delete(ALL); self.draw.rectangle([0, 0, CANVAS_WIDTH, CANVAS_HEIGHT], fill="white")
        for color in self.all_paths: self.all_paths[color] = []

    def createGCode(self):
        output_file = "drawing1.gcode"
        combined_gcode = ["M5"]
        has_data = False
        
        for color, paths in self.all_paths.items():
            if not paths: continue
            has_data = True
            
            # Insert the Color Specific Command
            cmd = self.color_commands[color]
            combined_gcode.append(cmd) 
            
            temp_file = "temp.gcode"
            gen = PathGcodeGenerator(paths, temp_file, (CANVAS_WIDTH, CANVAS_HEIGHT), (TARGET_WIDTH, TARGET_HEIGHT))
            success, _ = gen.generate()
            
            if success:
                with open(temp_file, 'r') as f:
                    content = [line.strip() for line in f.readlines()]
                    combined_gcode.extend(content)
                os.remove(temp_file)

        if has_data:
            combined_gcode.append("C0")
            combined_gcode.append("M2")
            with open(output_file, "w") as f:
                f.write("\n".join(combined_gcode))
            print(f"Success: File saved as {output_file}")
        else:
            print("Error: No drawings found.")

if __name__ == "__main__":
    App().mainloop()