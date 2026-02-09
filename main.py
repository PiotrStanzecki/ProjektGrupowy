from tkinter import *
from tkinter import colorchooser, ttk
from tkinter import filedialog as fd
from PIL import Image, ImageTk, ImageDraw 
from math import hypot
import numpy as np
import customtkinter


CANVAS_WIDTH = 500
CANVAS_HEIGHT = 400

TARGET_WIDTH = 150
TARGET_HEIGHT = 40 

class PathGcodeGenerator:
    def __init__(self, paths, output_file, canvas_size, target_size): 
        self.paths = paths
        self.output_file = output_file
        self.tolerance = 1.5

        canv = (canvas_size[0], canvas_size[1])

        canvas_w = canvas_size[0]

        self.paths = [
        [(canvas_w - x, y) for x, y in path] 
        for path in paths]

        self.paths = [t for t in self.paths 
                    if all(val >= 0 for coord in t for val in coord)]
        
        self.sx = target_size[0] / canvas_size[0]
        self.sy = target_size[1] / canvas_size[1]

    def dist(self, p1, p2):
        return hypot(p1[0] - p2[0], p1[1] - p2[1])

    def round_to_step(value, step):
        return round(value / step) * step

    def fmt(self, val, step):
        #val = round(val / step) * step
        return f"{val:.2f}".rstrip('0').rstrip('.')
        #return f"{str(int(round(val)))}".rstrip('0').rstrip('.')
        
    

    def generate(self):
        try:
            
            scaled_polylines = []
            
            for path in self.paths:
                if len(path) < 2: continue
                
                # Konwersja każdego punktu: x * sx, y * sy
                scaled_path = [(p[0] * self.sx, p[1] * self.sy) for p in path]
                scaled_polylines.append(scaled_path)

            if not scaled_polylines:
                return False, "Brak ścieżek do narysowania."

            #Sort
            ordered_paths = []
            cx, cy = 0.0, 0.0 
            
            #Kopia listy
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
                
                #Skok
                if self.dist((last_x, last_y), start_pt) > self.tolerance:
                    if pen_is_down:
                        g.append("M5"); pen_is_down = False

                    
                    
                    g.append(f"G01 X{self.fmt(start_pt[0], 0.023)} Y{self.fmt(start_pt[1], 0.043)}")
                    last_x, last_y = start_pt
                
                # Pisak w dół
                if not pen_is_down:
                    g.append("M3"); pen_is_down = True
                
                # Rysowanie linii
                for pt in path[1:]:
                    #Duplikat
                    if self.dist((last_x, last_y), pt) > 0.005:
                        g.append(f"G01 X{self.fmt(pt[0], 0.01)} Y{self.fmt(pt[1], 0.01)}")
                        last_x, last_y = pt

            g.extend(["M5", "M2"])

            with open(self.output_file, 'w') as f:
                f.write('\n'.join(g))
            
            return True, len(g)

        except Exception as e:
            return False, str(e)


class main:
    def __init__(self, master):
        self.master = master
        self.colorFg = 'black'
        self.colorBg = 'white'
        self.penWidth = 5
        
    
        
        self.oldX = None
        self.oldY = None
        
        #Path memory
        self.all_paths = []     
        self.current_path = []  
        
        self.line_start_x = None
        self.line_start_y = None
        self.current_line_id = None
        
        
        self.image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "white")
        self.draw = ImageDraw.Draw(self.image)
        
        self.drawWidgets()
        self.enablePenTool()

    def clamp_x(self, x):
    
        if x < 0: return 0
        if x > CANVAS_WIDTH: return CANVAS_WIDTH
        return x

    def clamp_y(self, y):

        if y < 0: return 0
        if y > CANVAS_HEIGHT: return CANVAS_HEIGHT
        return y

    #Pen tool
    def enablePenTool(self):
        self.c.unbind('<Button-1>')
        self.c.bind('<B1-Motion>', self.paint)
        self.c.bind('<ButtonRelease-1>', self.reset)

    def paint(self, e):
        if self.oldX and self.oldY:
            self.c.create_line(self.oldX, self.oldY, e.x, e.y, 
                               width=self.penWidth, fill=self.colorFg, 
                               capstyle='round', smooth=True)
            self.draw.line([self.oldX, self.oldY, e.x, e.y], 
                           fill=self.colorFg, width=self.penWidth)

        self.oldX = e.x
        self.oldY = e.y
        self.current_path.append((e.x, e.y))

    def reset(self, e):
        self.oldX = None
        self.oldY = None
        if len(self.current_path) > 1:
            self.all_paths.append(self.current_path)
        self.current_path = []

    #Line tool
    def enableLineTool(self):
        self.c.unbind('<B1-Motion>')
        self.c.bind('<Button-1>', self.startLine)
        self.c.bind('<B1-Motion>', self.dragLine)
        self.c.bind('<ButtonRelease-1>', self.endLine)

    def startLine(self, e):
        self.line_start_x = e.x
        self.line_start_y = e.y
        self.current_line_id = self.c.create_line(e.x, e.y, e.x, e.y, fill=self.colorFg, width=self.penWidth)

    def dragLine(self, e):
        if self.current_line_id:
            self.c.coords(self.current_line_id, self.line_start_x, self.line_start_y, e.x, e.y)

    def endLine(self, e):
        if self.current_line_id:
            self.c.coords(self.current_line_id, self.line_start_x, self.line_start_y, e.x, e.y)
            self.draw.line([self.line_start_x, self.line_start_y, e.x, e.y], fill=self.colorFg, width=self.penWidth)
            self.current_line_id = None
            self.all_paths.append([(self.line_start_x, self.line_start_y), (e.x, e.y)])

    #Circle tool
    def drawCircle(self, Rad):
        
        self.c.unbind('<Button-1>')
        self.c.unbind('<B1-Motion>')
        self.c.unbind('<ButtonRelease-1>')
        
        
        radius = Rad.get()
        
        self.c.bind('<Button-1>', lambda e: self.circle(e, radius))
        
    def circle(self, e, Rad):
        N = 120
        R = Rad
        x = []
        y = []
        xc = []
        yc = []
        offs = 4
        points = []
        for i in range(0, N + 1):
            if (e.x < R | e.y < R | CANVAS_WIDTH - e.x < R | CANVAS_HEIGHT - e.y < R ):
                print("ERROR, nie odpowiednie koło")
                break
            x.append(e.x + R * np.sin(2 * np.pi * i / N))
            y.append(e.y + R * np.cos(2 * np.pi * i / N))
            self.c.create_oval(x[i] - self.penWidth + offs,y[i] + self.penWidth - offs, x[i] + self.penWidth - offs, y[i] - self.penWidth + offs)
            xc.append(e.x + R/2 * CANVAS_WIDTH / TARGET_WIDTH * np.sin(2 * np.pi * i / N))
            yc.append(e.y + R/2 * CANVAS_HEIGHT / TARGET_HEIGHT * np.cos(2 * np.pi * i / N))
            
            points.append((xc[i] , yc[i]))
        
        flat_points = [coord for p in points for coord in p]

        #for i in range(1, len(x)):
            #self.c.create_line(x[i],y[i],x[i-1],y[i-1], fill = 'black', width=self.penWidth)

        self.all_paths.append(points)
        
        self.enablePenTool()

        
            

        


    

    #Generowanie Gcode
    def createGCode(self):
        print("Generowanie G-code...")
        output_filename = "drawing.gcode"
        
       
        generator = PathGcodeGenerator(
            self.all_paths, 
            output_filename, 
            canvas_size=(CANVAS_WIDTH, CANVAS_HEIGHT),
            target_size=(TARGET_WIDTH, TARGET_HEIGHT)
        )
        
        success, info = generator.generate()
        
        if success:
            print(f"Zapisano {info} linii w '{output_filename}'.")
        else:
            print(f"BŁĄD: {info}")

    def clearCanv(self):
        self.c.delete(ALL)
        self.draw.rectangle([0, 0, CANVAS_WIDTH, CANVAS_HEIGHT], fill="white")
        self.all_paths = []
        
    def changeColor(self, color):
        self.colorFg = color
        self.enablePenTool()

    def createColorImage(self, color, size=(16, 16)):
        img = Image.new('RGB', size, color)
        return ImageTk.PhotoImage(img)
    
    def chbutton (self,var):
        if var.get() == 1:
            self.enableLineTool()
        elif var.get() == 0:
            self.enablePenTool()


    def drawWidgets(self):
        self.controls = Frame(self.master, padx = 5 , pady = 5, bg = 'gray')
        #self.controls.place(relx=0, rely=0, relwidth=0.1, relheight=1.0)
        self.controls.pack(side=LEFT, fill = Y)
        self.checkvar = IntVar()
        self.val1 = IntVar()
        
        self.red_img = self.createColorImage('red')
        self.blue_img = self.createColorImage('blue')
        self.black_img = self.createColorImage('black')

        Button(self.controls, text="Red", image=self.red_img, compound=LEFT, command=lambda: self.changeColor('red')).pack(pady=5, fill=X)
        Button(self.controls, text="Blue", image=self.blue_img, compound=LEFT, command=lambda: self.changeColor('blue')).pack(pady=5, fill=X)
        Button(self.controls, text="Black", image=self.black_img, compound=LEFT, command=lambda: self.changeColor('black')).pack(pady=5, fill=X)
        
        Checkbutton(self.controls, text="Line",variable = self.checkvar, onvalue=1, offvalue=0,  command= lambda: self.chbutton(self.checkvar)).pack(pady=5, fill=X)
        Button(self.controls, text="Circle", command=lambda:self.drawCircle(self.val1)).pack(pady=5, fill=X)
        Scale(self.controls, from_= 0, to = 30, orient= HORIZONTAL, variable=self.val1, label="Radius" ).pack(pady=5, fill=X)
        Button(self.controls, text="G-CODE", command=self.createGCode, bg='lightgreen').pack(pady=5, fill=X)
        Button(self.controls, text="Clear", command=self.clearCanv, bg='#ffcccc').pack(pady=5, fill=X)
        

        self.c = Canvas(self.master, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg=self.colorBg)
        #self.c.place(relx=0.1, rely=0, relwidth=0.9, relheight=1.0)
        self.c.pack(side=LEFT)


win = Tk()
win.title("G-Code Paint")
win.geometry("600x400")
win.resizable(False,False)
main(win)
win.mainloop()