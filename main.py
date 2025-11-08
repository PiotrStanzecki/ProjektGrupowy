from tkinter import *
from tkinter import colorchooser, ttk
import numpy as np
from PIL import Image, ImageTk 

class position:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color

class main:
    def __init__(self, master):
        self.master = master
        self.colorFg = 'black'
        self.colorBg = 'white'
        self.oldX = None
        self.oldY = None
        self.penWidth = 5
        self.drawWidgets()
        self.c.bind('<B1-Motion>', self.paint)
        self.c.bind('<ButtonRelease-1>', self.reset)
        self.posArray = []


    def paint(self, e):
        if self.oldX and self.oldY:
            self.c.create_line(self.oldX, self.oldY, e.x, e.y, width = self.penWidth, fill = self.colorFg, capstyle = 'round', smooth = True)
        self.oldX = e.x
        self.oldY = e.y

        match self.colorFg:
            case 'black':
                print("black", e.x, e.y)
                self.posArray.append(position(e.x, e.y, 'black'))
            case 'blue':
                print("blue", e.x, e.y)
                self.posArray.append(position(e.x, e.y, 'blue'))
            case 'red':
                print("red", e.x, e.y)
                self.posArray.append(position(e.x, e.y, 'red'))
            case _:
                print("error")



    
    def load(self):
        for pos in self.posArray:
            self.c.create_oval(
                pos.x, 
                pos.y, 
                pos.x + self.penWidth, 
                pos.y + self.penWidth, 
                fill=pos.color,
                outline=pos.color 
            )
        


    def reset(self, e):
        self.oldX = None
        self.oldY = None

    def clearCanv(self):
        self.c.delete(ALL)
        #self.posArray = None

    def clearLoad(self):
        self.posArray = None
    
    def changeColor(self, color):
        self.colorFg = color
    

    def create_color_image(self, color, size=(16, 16)):
        img = Image.new('RGB', size, color)
        return ImageTk.PhotoImage(img)


    def drawWidgets(self):

        self.controls = Frame(self.master, padx = 5 , pady = 5, bg = 'gray')
        self.controls.place(relx=0, rely=0, relwidth=0.1, relheight=1.0)

        
        self.red_img = self.create_color_image('red')
        self.blue_img = self.create_color_image('blue')
        self.black_img = self.create_color_image('black')


        redButton = Button(self.controls, text = "Red", image=self.red_img, compound=LEFT, 
                           command = lambda: self.changeColor('red'), bg = 'lightgray')
        redButton.pack(anchor = 'n', pady=5, fill=X) 


        blueButton = Button(self.controls, text = "Blue", image=self.blue_img, compound=LEFT,
                            command = lambda: self.changeColor('blue'), bg = 'lightgray')
        blueButton.pack(anchor = 'n', pady=5, fill=X) 


        blackButton = Button(self.controls, text = "Black", image=self.black_img, compound=LEFT,
                             command = lambda: self.changeColor('black'), bg = 'lightgray')
        blackButton.pack(anchor = 'n', pady=5, fill=X) 

        loadButton = Button(self.controls, text = "load", compound=LEFT,
                             command = self.load, bg = 'lightgray')
        loadButton.pack(anchor = 'n', pady=5, fill=X) 
        
        

        
        
        

        self.c = Canvas(self.master, width = 500, height = 400, bg = self.colorBg)
        self.c.place(relx=0.1, rely=0, relwidth=0.9, relheight=1.0)

        menu = Menu(self.master)
        self.master.config(menu = menu)
        optionmenu = Menu(menu)
        menu.add_cascade(label = 'Menu', menu = optionmenu)
        optionmenu.add_command(label = 'Clear canvas', command = self.clearCanv)
        optionmenu.add_command(label = 'Clear Load', command = self.clearLoad)

        
win = Tk()
win.title("Paint")
win.geometry("600x450")
main(win)
win.mainloop()