import tkinter as tk
import tkinter.font as tkfont
from tkinter.ttk import Progressbar, Style
from PIL import ImageTk, Image, ImageDraw
from webcolors import name_to_rgb
from textwrap import wrap
from skimage.transform import resize
import cv2
import numpy as np
from multiprocessing import Queue, Value

imgh = 180
imgw = 320

class RoundedFrame(tk.Canvas):
    def __init__(self, 
                 master = None, 
                 text: str = "", 
                 radius: int = 35, 
                 foreground = "#000000", 
                 font = 'Jost',
                 fontsize = 10,
                 fontprops = 'normal', 
                 background = "#ffffff", 
                 contour_color = '',
                 contour_width = 0,
                 *args, **kwargs):
        super(RoundedFrame, self).__init__(master, highlightthickness=0, *args, **kwargs)
        self.config(bg=self.master["bg"])
        self.background = background
        self.foreground = foreground
        self.base_fontsize = fontsize
        
        self.outline = contour_color
    
        self.radius = radius        
        
        self.rect = self.round_rectangle(0, 0, 0, 0, 
                                         radius=radius, 
                                         fill=background, 
                                         width=contour_width,
                                         outline=contour_color)
        
        self.text_font = tkfont.Font(family=font, size=fontsize, weight=fontprops)
        self.text = self.create_text(0, 0, text=text, fill=foreground, font=self.text_font, justify="center")

        self.bind("<Configure>", self.resize)
          
    def round_rectangle(self, x1, y1, x2, y2, radius=25, update=False, **kwargs): 
        points = [
            x1 + radius, y1,
            x1 + radius, y1,
            x2 - radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1 + radius,
            x1, y1
        ]

        if not update:
            return self.create_polygon(points, smooth=True, **kwargs)
        else:
            self.coords(self.rect, points)

    def resize(self, event):
        if isinstance(event, tk.Event):
            width, height = event.width, event.height
        else:
            width, height = event
        if self.radius > width or self.radius > height:
            radius = min(width, height)
        else:
            radius = self.radius
        self.configure(width=width, height=height)
        self.round_rectangle(5, 5, width-5, height-5, radius, outline=self.outline, update=True)

        bbox = self.bbox(self.rect)

        text_bbox = self.bbox(self.text)
        if text_bbox:
            x = ((bbox[2] - bbox[0]) / 2) - ((text_bbox[2] - text_bbox[0]) / 2)
            y = ((bbox[3] - bbox[1]) / 2) - ((text_bbox[3] - text_bbox[1]) / 2)
            self.moveto(self.text, x, y)

    def change_color(self, color):
        self.itemconfig(self.rect, fill=color)
        self.background = color
        
    def change_text(self, text):
        self.itemconfig(self.text, text=text)
        
        bbox = self.bbox(self.text)
        w = bbox[2] - bbox[0]
        if w > self.winfo_width():
            average_char_width = w / len(text)
            chars_per_line = int(self.winfo_width() / average_char_width)
            while w > self.winfo_width():  
                wrapped_text = '\n'.join(wrap(text, chars_per_line))
                self.itemconfig(self.text, text=wrapped_text)
                self.update()
                chars_per_line -= 1
                bbox = self.bbox(self.text)
                w = bbox[2] - bbox[0]
                

class RoundedButton(RoundedFrame):
    def __init__(
        self,
        master,
        btnpressclr = "#d2d6d3",
        callback = None, 
        *args, **kwargs
    ):
        super(RoundedButton, self).__init__(master, *args, **kwargs)
        self.btnpressclr = btnpressclr
        self.callback = callback
        
        self.addtag('button', 'withtag', self.rect)
        self.addtag('button', 'withtag', self.text)
        self.tag_bind("button", "<ButtonPress>", self.border)
        self.tag_bind("button", "<ButtonRelease>", self.border)
        
    def border(self, event):
        if event.type == "4":
            self.itemconfig(self.rect, fill=self.btnpressclr)
            if self.callback is not None:
                self.callback()
        else:
            self.itemconfig(self.rect, fill=self.background)

def add_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
    alpha = Image.new('L', im.size, "white")
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im

class App():
    def __init__(self):
        global imgw, imgh
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)

        self.line_id = None
        self.line_points = []
        self.line_options = {'fill': 'black', 'width': 10}
        
        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        #конфигурируем панель управления
        self.fr_ctrl = tk.Frame(self.canvas, bg="lightgrey", highlightthickness=0)
        self.fr_ctrl.place(relx=0, rely=0, relwidth=0.2, relheight=1)   
        self.root.update()  
        
        imgw = int(imgw * self.root.winfo_width() / 1440)
        imgh = int(imgh * self.root.winfo_height() / 899)
        
        self.fr_ctrl.columnconfigure(0, weight=0)

        # self.canvas.bind('<Button-1>', self.set_start)
        # self.canvas.bind('<B1-Motion>', self.draw_line)
        # self.canvas.bind('<ButtonRelease-1>', lambda x: self.end_line())
        self.btfont = 'Jost'
        self.fontsize = int(35 * self.root.winfo_width() / 1440)
        self.fontprops = 'bold'
        self.pad = 10
        self.btclr = '#6d2222'
        self.btpress = '#e77774'
        self.bttextclr = 'white'
        
        self.image_panel = tk.Label(self.canvas)

        self.points_image = ImageTk.PhotoImage(Image.fromarray(np.ones((imgh, imgw))))
        self.points_image_panel = tk.Label(self.fr_ctrl, image=self.points_image, bg="lightgrey")
        self.points_image_panel.pack(side='top', fill='both', pady=self.pad, padx=5)
        
        self.camera_image = None
        
        self.status_drawing = RoundedFrame(
            master=self.fr_ctrl,
            background='red', 
            bg='red',
            font="Jost",
            fontsize=15,
            height=200 * self.root.winfo_width() / 1440
        )
        self.status_drawing.pack(side='top', fill='both', pady=self.pad)
        self.now_clr = 'red'
        
        self.bth = (self.root.winfo_height() - 11 * 10 - imgh - 200 * self.root.winfo_width() / 1440) / 3
        self.btw = 20
        
        self.fr_status = tk.Frame(self.fr_ctrl, highlightthickness=0, bg='lightgrey')
        self.fr_status.pack(side='top', fill='both', pady=self.pad)

        #кнопка очистки
        self.bt_del = RoundedButton(
            self.fr_ctrl,
            text='Очистить', 
            callback=self.delete,
            height=self.bth,
            background=self.btclr,
            foreground=self.bttextclr,
            btnpressclr=self.btpress,
            font=self.btfont,
            fontsize=self.fontsize,
            fontprops=self.fontprops
        )
        self.bt_del.pack(fill='x', side='top', pady=self.pad)

        #всплывающее окно с изменением цвета
        self.clrs = ['red', 'green', 'blue', 'black', 'gray', 'yellow', 'brown', 'purple', 'cyan', 'white']
        self.rgbclrs = {x: name_to_rgb(x) for x in self.clrs}

        #кнопка изменения толщины
        self.bt_set_wd = RoundedButton(
            self.fr_ctrl, 
            text='Толщина', 
            callback=self.setup_wd_popup, 
            relief='groove', 
            height=self.bth,
            btnpressclr=self.btpress,
            foreground=self.bttextclr,
            background=self.btclr,
            font=self.btfont,
            fontsize=self.fontsize,
            fontprops=self.fontprops
        )
        self.bt_set_wd.pack(side='top', fill='x', pady=self.pad)
        
        self.fr_wd_set = RoundedFrame(contour_color='#a72525', contour_width=5, width=200, bg='white')
        
        for i in range(3, 16, 3):
            cv = tk.Canvas(self.fr_wd_set, width=200, height=40, bg='white', highlightthickness=0)
            line = tk.Frame(cv, height=i, width=190, bg='black')
            cv.bind('<ButtonPress>', lambda x, k = i: self.change_width(k))
            cv.grid(row=i // 2, column=0, padx=10, pady=12)
            line.bind('<ButtonPress>', lambda x, k = i: self.change_width(k))
            line.pack(padx=5, pady=10)

        #кнопка генерации
        self.bt_gen = RoundedButton(
            self.fr_ctrl,
            background=self.btclr,
            foreground=self.bttextclr,
            callback=self.gen,
            text='Готово!', 
            height=self.bth,
            btnpressclr=self.btpress,
            font=self.btfont,
            fontsize=self.fontsize,
            fontprops=self.fontprops
        )
        self.bt_gen.pack(side='top', fill='x', pady=self.pad)

        #картинка, чтобы затем генерировать
        self.image = Image.new("RGB", (512, 512), (255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)
        
        #предыдущие высота и ширина canvas
        self.prevw = 0
        self.prevh = 0
        
        self.fr_progressbar = tk.Frame(self.fr_status, height=60, highlightthickness=0, bg='lightgrey')
        
        self.progressval = 0
        self.progressmax = 50
        
        self.style = Style(self.root)
        self.style.layout('text.Horizontal.TProgressbar',
                    [('Horizontal.Progressbar.trough',
                    {'children': [('Horizontal.Progressbar.pbar',
                                    {'side': 'left', 'sticky': 'ns'})],
                        'sticky': 'nswe'}),
                    ('Horizontal.Progressbar.label', {'sticky': ''})])
        self.style.configure('text.Horizontal.TProgressbar', text=f'0/{self.progressmax}', background='cyan', font='Jost 20')

        self.progressbar = Progressbar(self.fr_progressbar, style='text.Horizontal.TProgressbar', length=200, maximum=self.progressmax)
        self.lb_progressbar = tk.Label(self.fr_progressbar, text='Идет обработка, подождите...', font='Jost 16')
        
        self.bt_yes = RoundedButton(
            self.fr_status, 
            text="Да", 
            callback=self.change_flags_correct,
            font="Jost",
            fontsize=int(25 * self.root.winfo_width() / 1440),
            background=self.btclr,
            foreground='white'
        )
        
        self.bt_no = RoundedButton(
            self.fr_status, 
            text="Нет", 
            font="Jost",
            fontsize=int(25 * self.root.winfo_width() / 1440),
            callback=self.change_flags_incorrect, 
            background=self.btclr,
            foreground='white'
        )
        
        self.actions = []
        self.flag_generate = 0
        
        self.bt_del.bind('<Button-1>', lambda x: self.del_popups())
        self.bt_gen.bind('<Button-1>', lambda x: self.del_popups())
        self.fr_ctrl.bind('<Button-1>', lambda x: self.del_popups())
        self.fr_status.bind('<Button-1>', lambda x: self.del_popups())
        self.points_image_panel.bind('<Button-1>', lambda x: self.del_popups())
        self.status_drawing.bind('<Button-1>', lambda x: self.del_popups())
        
        self.print_instructions()
    
    def setup_wd_popup(self):
        self.fr_wd_set.place(x=self.bt_set_wd.winfo_width() + 5, y=self.bt_set_wd.winfo_y() - 100)

    def del_popups(self):
        self.fr_wd_set.place_forget()
        
    def gen(self):
        self.flag_generate = 1
    
    def change_flags_correct(self):
        self.flag_recognition.value = 1
        self.flag_answer.value = 1
    
    def change_flags_incorrect(self):
        self.flag_recognition.value = 0
        self.flag_answer.value = 1
        
    def print_instructions(self):
        text = ["- начать/закончить", "- перемещать курсор", "- рисовать", "- очистить все"]
        imgs_names = ["thumb_up.png", "point_up.png", "click.png", "open.png"]
        self.instruction_frame = tk.Frame(self.canvas, bg="white")
        self.instruction_frame.pack(fill='both', padx=(self.fr_ctrl.winfo_width(), 0))
        self.signs = []
        for idx, sentence in enumerate(text):
            label = tk.Label(self.instruction_frame, text=sentence, font="Jost 50", bg='white', fg='black')
            self.signs.append(ImageTk.PhotoImage(Image.open('images/' + imgs_names[idx])))
            image = tk.Label(self.instruction_frame, image=self.signs[-1], bg='white')
            
            image.grid(row=idx, column=0)
            label.grid(row=idx, column=1, sticky='w')
        
    def remove_instructions(self):
        self.instruction_frame.pack_forget()
                
    def change_status(self):
        if self.now_clr == "red": self.now_clr = "green"
        elif self.now_clr == "green": self.now_clr = "yellow"
        elif self.now_clr == "yellow": self.now_clr = "red"
        self.status_drawing.change_color(self.now_clr)
                
    def progressbar_step(self, amount):        
        self.progressval = (self.progressval + amount) % (self.progressmax + 1)
        if self.progressval == 0:
            self.progressval = 1
        self.style.configure('text.Horizontal.TProgressbar', text=f'{self.progressval}/{self.progressmax}')
        self.progressbar.step(amount)
                
    def check_recognition(self):
        self.status_drawing.resize((self.fr_status.winfo_width(), 200 * self.root.winfo_width() / 1440 / 2))
        self.bt_yes.configure(width=self.fr_ctrl.winfo_width() // 2 - 5, height=100)
        self.bt_no.configure(width=self.fr_ctrl.winfo_width() // 2 - 5, height=100)
        self.bt_yes.pack(side='left')
        self.bt_no.pack(side='left')
        
    def setup_progressbar(self):
        self.bt_yes.pack_forget()
        self.bt_no.pack_forget()
        
        self.fr_progressbar.pack(anchor='s', fill='x', padx=15, pady=2)
        self.fr_progressbar.pack_propagate(False)
        
        self.progressbar.pack(fill='both')
        self.lb_progressbar.pack()
        self.lb_progressbar.pack()
        
        
    def set_start(self, cords):
        if isinstance(cords, tk.Event):
            x, y = cords.x, cords.y
        else:
            x, y = cords
        if x >= self.fr_ctrl.winfo_width():
            self.line_points.append((x, y))
        self.del_popups()

    def draw_line(self, cords):
        if isinstance(cords, tk.Event):
            x, y = cords.x, cords.y
        else:
            x, y = cords
        self.line_points.append((x, y))
        if len(self.line_points) >= 2:
            if self.line_id is not None:
                self.canvas.delete(self.line_id)
            self.line_id = self.canvas.create_line(self.line_points, **self.line_options)
            self.draw.line(self.line_points, **self.line_options)
            # self.actions.append(lambda: self.draw.line(self.line_points, **self.line_options))

    def end_line(self):
        self.line_points.clear()
        self.line_id = None

    def delete(self):
        self.end_line()
        self.canvas.delete("all")
        self.image = Image.new("RGB", (self.canvas.winfo_width(), self.canvas.winfo_height()), (255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)
        self.actions.clear()

    def change_width(self, x):
        self.line_options['width'] = x
        print(x)
        self.fr_wd_set.place_forget()

    def update(self):
        if not self.frames_queue.empty():
            image = self.frames_queue.get().image
            image = Image.fromarray(image.astype('uint8')).resize((imgw, imgh))
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
            image = add_corners(image, 35)
            self.points_image = ImageTk.PhotoImage(image)
            self.points_image_panel.configure(image=self.points_image)
        
        h, w = self.canvas.winfo_height(), self.canvas.winfo_width()
        if w != self.prevw or h != self.prevh:
            self.image = self.image.resize((w, h))
            self.draw = ImageDraw.Draw(self.image)
            self.prevh = h
            self.prevw = w
            for action in self.actions:
                action()
        
        self.canvas_w.value = self.canvas.winfo_width()
        self.canvas_h.value = self.canvas.winfo_height()
        
        self.shiftx.value = self.root.winfo_x()
        self.shifty.value = self.root.winfo_y()
        
        if not self.commands_queue.empty():
            f, args = self.commands_queue.get()
            func = getattr(self, f)
            if args is None: func()
            else: func(*args)
        self.root.update()
                
    def mainloop(
        self, 
        frames_queue: Queue, 
        commands_queue: Queue, 
        canvas_w, canvas_h, 
        shiftx, shifty,
        flag_recognition, flag_recognition_result
    ):
        self.frames_queue = frames_queue
        self.commands_queue = commands_queue
        
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h        
        
        self.shiftx = shiftx
        self.shifty = shifty
        
        self.flag_recognition = flag_recognition
        self.flag_answer = flag_recognition_result
        
        self.running = True
        while self.running:
            self.update()
                
    def print_text(self, text):
        self.status_drawing.change_text(text)
                        
    def remove_img(self):
        self.image_panel.pack_forget()
    
    def display(self, img: Image):
        if img.size[0] < img.size[1]:
            img = img.resize((self.canvas.winfo_width(),  int(self.canvas.winfo_width() / img.size[0] * img.size[1])))
        else: 
            img = img.resize((int(self.canvas.winfo_height() / img.size[1] * img.size[0]), self.canvas.winfo_height()))
        self.display_img = ImageTk.PhotoImage(img)
        self.image_panel.configure(image=self.display_img)
        self.image_panel.pack(side="bottom", fill="both", expand="yes")