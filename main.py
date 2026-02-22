import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import threading
import time
from tkinter import Canvas
import keyboard
from PIL import Image, ImageDraw, ImageTk
import cv2
import numpy as np
from mss import mss
import pyautogui


def detect_green_presence(x, y, width, height):

    try:
      
        with mss() as sct:
            monitor = {
                'top': y,
                'left': x,
                'width': width,
                'height': height
            }
            screenshot = np.array(sct.grab(monitor))

        hsv_image = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)

        lower_green = np.array([30, 40, 40])     
        upper_green = np.array([90, 255, 255])    
        
 
        mask = cv2.inRange(hsv_image, lower_green, upper_green)
        
    
        green_pixels = np.sum(mask > 0)
        total_pixels = mask.size
        green_percentage = (green_pixels / total_pixels) * 100
        
        return green_percentage
    
    except Exception as e:
        print(f" Error in detect_green_presence: {e}")
        return 0.0


class AreaSelectorWindow(tk.Toplevel):
 
    def __init__(self, parent, callback, initial_geometry=None):
        super().__init__(parent)
        self.callback = callback
        

        self.attributes('-fullscreen', True)
        self.attributes('-topmost', True)
        self.configure(bg='magenta')  # cor de transparência
        self.attributes('-transparentcolor', 'magenta')
        
 
        if initial_geometry:
            self.rect_x = initial_geometry['x']
            self.rect_y = initial_geometry['y']
            self.rect_width = initial_geometry['width']
            self.rect_height = initial_geometry['height']
        else:
            self.rect_x = 300
            self.rect_y = 300
            self.rect_width = 500
            self.rect_height = 300
        
   
        self.dragging = False
        self.resizing = False
        self.drag_start = None
        self.resize_edge = None
        self.handle_size = 25
        
  
        self.ok_button_rect = None
        
   
        self.label = tk.Label(self, bg='magenta')
        self.label.pack(fill=tk.BOTH, expand=True)
        self.label.bind('<Button-1>', self.on_mouse_down)
        self.label.bind('<B1-Motion>', self.on_mouse_move)
        self.label.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.bind('<Escape>', self.on_escape)
        self.label.bind('<Motion>', self.on_motion)
        self.label.focus_set()
        
        # Timer para redesenho
        self.update_image()
        
    
    def update_image(self):

        try:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            

            img = Image.new('RGBA', (screen_width, screen_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
     
            draw.rectangle(
                [self.rect_x, self.rect_y, self.rect_x + self.rect_width, self.rect_y + self.rect_height],
                outline='#a060d0', width=3, fill=None
            )
            
       
            handle_size = 7
            handle_positions = [
                (self.rect_x, self.rect_y),
                (self.rect_x + self.rect_width, self.rect_y),
                (self.rect_x, self.rect_y + self.rect_height),
                (self.rect_x + self.rect_width, self.rect_y + self.rect_height),
            ]
            
            for x, y in handle_positions:
                draw.rectangle(
                    [x - handle_size, y - handle_size, x + handle_size, y + handle_size],
                    fill='#a060d0', outline='#a060d0'
                )
            
            info_text = f"Pos: ({self.rect_x}, {self.rect_y}) | Size: {self.rect_width}x{self.rect_height}"
            instructions = "Drag: Move | Drag Corners: Resize | Click OK to Save"
            draw.text((20, 30), info_text, fill=(160, 96, 208, 255), font=None)
            draw.text((20, 55), instructions, fill=(160, 96, 208, 255), font=None)
            
    
            button_width = 120
            button_height = 50
            button_x = screen_width - button_width - 20
            button_y = screen_height - button_height - 20
            
      
            self.ok_button_rect = (button_x, button_y, button_x + button_width, button_y + button_height)
            
          
            draw.rectangle(self.ok_button_rect, fill=(160, 96, 208, 255), outline=(255, 255, 255, 255), width=2)
            
     
            text_bbox = draw.textbbox((0, 0), "OK")
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = button_x + (button_width - text_width) // 2
            text_y = button_y + (button_height - text_height) // 2
            draw.text((text_x, text_y), "OK", fill=(30, 30, 30, 255), font=None)
            
     
            self.photo = ImageTk.PhotoImage(img)
            self.label.config(image=self.photo)
            self.after(16, self.update_image)
        except Exception as e:
            self.after(16, self.update_image)
    
    def get_resize_edge(self, x, y):
     
        h = self.handle_size
        
        if x < self.rect_x + h and y < self.rect_y + h:
            return 'top-left'
        if x > self.rect_x + self.rect_width - h and y < self.rect_y + h:
            return 'top-right'
        if x < self.rect_x + h and y > self.rect_y + self.rect_height - h:
            return 'bottom-left'
        if x > self.rect_x + self.rect_width - h and y > self.rect_y + self.rect_height - h:
            return 'bottom-right'
        
        if abs(x - self.rect_x) < h and self.rect_y < y < self.rect_y + self.rect_height:
            return 'left'
        if abs(x - (self.rect_x + self.rect_width)) < h and self.rect_y < y < self.rect_y + self.rect_height:
            return 'right'
        if abs(y - self.rect_y) < h and self.rect_x < x < self.rect_x + self.rect_width:
            return 'top'
        if abs(y - (self.rect_y + self.rect_height)) < h and self.rect_x < x < self.rect_x + self.rect_width:
            return 'bottom'
        
        return None
    
    def on_motion(self, event):
   
        x, y = event.x, event.y
        edge = self.get_resize_edge(x, y)
        
        # Verificar se está sobre o botão OK
        if self.ok_button_rect and self.is_over_ok_button(x, y):
            self.config(cursor='hand2')
        elif edge in ['top-left', 'bottom-right']:
            self.config(cursor='nwse_resize')
        elif edge in ['top-right', 'bottom-left']:
            self.config(cursor='nesw_resize')
        elif edge in ['left', 'right']:
            self.config(cursor='we_resize')
        elif edge in ['top', 'bottom']:
            self.config(cursor='ns_resize')
        elif self.rect_x < x < self.rect_x + self.rect_width and self.rect_y < y < self.rect_y + self.rect_height:
            self.config(cursor='fleur')
        else:
            self.config(cursor='crosshair')
    
    def is_over_ok_button(self, x, y):

        if not self.ok_button_rect:
            return False
        x1, y1, x2, y2 = self.ok_button_rect
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def on_mouse_down(self, event):
   
        x, y = event.x, event.y
        
   
        if self.is_over_ok_button(x, y):
            self.on_enter(event)
            return
        
        self.drag_start = (x, y)
        
     
        edge = self.get_resize_edge(x, y)
        if edge:
            self.resizing = True
            self.resize_edge = edge
    
        elif self.rect_x < x < self.rect_x + self.rect_width and self.rect_y < y < self.rect_y + self.rect_height:
            self.dragging = True
    
    def on_mouse_move(self, event):
     
        if not self.drag_start:
            return
        
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        
        if self.dragging:
            self.rect_x += dx
            self.rect_y += dy
          
            self.rect_x = max(0, min(self.rect_x, self.winfo_screenwidth() - self.rect_width))
            self.rect_y = max(0, min(self.rect_y, self.winfo_screenheight() - self.rect_height))
        
        elif self.resizing:
            edge = self.resize_edge
            old_x, old_y, old_w, old_h = self.rect_x, self.rect_y, self.rect_width, self.rect_height
            if edge == 'top-left':
                self.rect_x += dx
                self.rect_y += dy
                self.rect_width -= dx
                self.rect_height -= dy
            elif edge == 'top-right':
                self.rect_y += dy
                self.rect_width += dx
                self.rect_height -= dy
            elif edge == 'bottom-left':
                self.rect_x += dx
                self.rect_width -= dx
                self.rect_height += dy
            elif edge == 'bottom-right':
                self.rect_width += dx
                self.rect_height += dy
            elif edge == 'left':
                self.rect_x += dx
                self.rect_width -= dx
            elif edge == 'right':
                self.rect_width += dx
            elif edge == 'top':
                self.rect_y += dy
                self.rect_height -= dy
            elif edge == 'bottom':
                self.rect_height += dy
  
            if self.rect_width < 50:
                self.rect_width = 50
                self.rect_x = old_x + old_w - 50 if edge in ['top-left','bottom-left','left'] else self.rect_x
            if self.rect_height < 50:
                self.rect_height = 50
                self.rect_y = old_y + old_h - 50 if edge in ['top-left','top-right','top'] else self.rect_y
       
            self.rect_x = max(0, min(self.rect_x, self.winfo_screenwidth() - self.rect_width))
            self.rect_y = max(0, min(self.rect_y, self.winfo_screenheight() - self.rect_height))
        
        self.drag_start = (event.x, event.y)
    
    def on_mouse_up(self, event):
    
        self.dragging = False
        self.resizing = False
        self.resize_edge = None
        self.drag_start = None
    
    def on_enter(self, event):
       
        area_data = {
            'x': self.rect_x,
            'y': self.rect_y,
            'width': self.rect_width,
            'height': self.rect_height
        }
        if self.callback:
            self.callback(area_data)
        self.destroy()
    
    def on_escape(self, event):
   
        self.destroy()


class KeybindDialog(tk.Toplevel):
 
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.geometry('400x150')
        self.configure(bg='#1e1e1e')
        self.key_pressed = None
        self.attributes('-topmost', True)
        
        # Label
        label = tk.Label(self, text=f"Press any key for '{title}'...", 
                        bg='#1e1e1e', fg='#a060d0', font=('Arial', 12))
        label.pack(pady=20)
        
     
        self.bind('<Key>', self.on_key)
        self.focus_set()
    
    def on_key(self, event):
      
        self.key_pressed = event.keysym.upper()
        self.destroy()


class SomelleAutoTotem:
    def __init__(self, root):
        self.root = root
        self.config_file = "config.json"
        self.config = self.load_config()
        self.is_running = False
        self.area_window = None
        self.keybinds = {
            'start': self.config['keybinds'].get('start'),
            'area': self.config['keybinds'].get('area'),
            'exit': self.config['keybinds'].get('exit')
        }
        
        self.setup_ui()
        self.setup_global_keybinds()
    
    def load_config(self):
  
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return self.get_default_config()
        return self.get_default_config()
    
    def get_default_config(self):
    
        return {
            'keybinds': {'start': None, 'area': None, 'exit': None},
            'totems': {
                'first': '', 'second': '', 'second_enabled': False,
                'third': '', 'third_enabled': False,
                'fourth': '', 'fourth_enabled': False
            },
            'delay': 0.5,
            'action_delay': 1.4,
            'cycle_cooldown': 60.0,
            'start_cooldown': 7.0,
            'item_press_delay': 0.1,
            'area': {'x': 7, 'y': 985, 'width': 68, 'height': 74}
        }
    
    def save_config(self):
        """Salvar configurações em JSON"""
        self.config['keybinds'] = self.keybinds
        self.config['totems'] = {
            'first': self.first_entry.get(),
            'second': self.second_entry.get(),
            'second_enabled': self.second_var.get(),
            'third': self.third_entry.get(),
            'third_enabled': self.third_var.get(),
            'fourth': self.fourth_entry.get(),
            'fourth_enabled': self.fourth_var.get(),
        }
        self.config['delay'] = float(self.delay_spinbox.get())
        self.config['action_delay'] = float(self.action_delay_spinbox.get())
        self.config['cycle_cooldown'] = float(self.cycle_cooldown_spinbox.get())
        self.config['start_cooldown'] = float(self.start_cooldown_spinbox.get())
        self.config['item_press_delay'] = float(self.item_press_delay_spinbox.get())
        
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def setup_ui(self):
    
        self.root.title("Somelle Auto Totem Pro Edition")
        self.root.geometry("900x700")
        self.root.configure(bg='#1e1e1e')
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', background='#2d2d2d', foreground='#a060d0')
        style.configure('TLabel', background='#1e1e1e', foreground='#a060d0')
        style.configure('TFrame', background='#1e1e1e')
        style.configure('TEntry', fieldbackground='#2d2d2d', foreground='#a060d0')
        style.configure('TCheckbutton', background='#1e1e1e', foreground='#a060d0')
        style.configure('TNotebook', background='#1e1e1e', borderwidth=0)
        style.configure('TNotebook.Tab', background='#1e1e1e', foreground='#a060d0', padding=[20, 10])
        style.configure('TLabelframe', background='#1e1e1e', foreground='#a060d0', borderwidth=1)
        style.configure('TLabelframe.Label', background='#1e1e1e', foreground='#a060d0')
        style.configure('TSpinbox', fieldbackground='#2d2d2d', foreground='#a060d0')
        
 
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        

        title = tk.Label(main_frame, text="Somelle Auto Totem Pro Edition",
                        bg='#1e1e1e', fg='#a060d0', font=('Arial', 24, 'bold'))
        title.pack(pady=15)
        
        # START/STOP Button
        self.start_stop_btn = tk.Button(main_frame, text="START", bg='#2d2d2d', 
                                       fg='#a060d0', font=('Arial', 14, 'bold'),
                                       height=3, command=self.toggle_start_stop,
                                       activebackground='#a060d0', activeforeground='#1e1e1e',
                                       relief=tk.RAISED, bd=2, borderwidth=3)
        self.start_stop_btn.pack(fill=tk.X, pady=10)
        
      
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
    
        keybind_frame = ttk.Frame(notebook)
        notebook.add(keybind_frame, text="⌨️ Keybinds")
        
        keybind_content = ttk.LabelFrame(keybind_frame, text="Set Your Keybinds", padding=15)
        keybind_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    
        fishing_inner = ttk.Frame(keybind_content)
        fishing_inner.pack(fill=tk.X, pady=5)
        ttk.Label(fishing_inner, text="Fishing Macro Start:").pack(side=tk.LEFT, padx=5)
        self.fishing_btn = tk.Button(fishing_inner, text="Set", 
                                    command=lambda: self.set_keybind('start'),
                                    bg='#a060d0', fg='#1e1e1e', width=10, font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2)
        self.fishing_btn.pack(side=tk.LEFT, padx=5)
        self.fishing_display = tk.Label(fishing_inner, text="Not set", 
                                       bg='#1e1e1e', fg='#a060d0', font=('Arial', 11, 'bold'))
        self.fishing_display.pack(side=tk.LEFT, padx=5)
        
      
        area_inner = ttk.Frame(keybind_content)
        area_inner.pack(fill=tk.X, pady=5)
        ttk.Label(area_inner, text="Invite Box Area:").pack(side=tk.LEFT, padx=5)
        self.area_btn = tk.Button(area_inner, text="Set",
                                 command=lambda: self.set_keybind('area'),
                                 bg='#a060d0', fg='#1e1e1e', width=10, font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2)
        self.area_btn.pack(side=tk.LEFT, padx=5)
        self.area_display = tk.Label(area_inner, text="Not set",
                                    bg='#1e1e1e', fg='#a060d0', font=('Arial', 11, 'bold'))
        self.area_display.pack(side=tk.LEFT, padx=5)
        

        exit_inner = ttk.Frame(keybind_content)
        exit_inner.pack(fill=tk.X, pady=5)
        ttk.Label(exit_inner, text="Exit Program:").pack(side=tk.LEFT, padx=5)
        self.exit_btn = tk.Button(exit_inner, text="Set",
                                 command=lambda: self.set_keybind('exit'),
                                 bg='#a060d0', fg='#1e1e1e', width=10, font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2)
        self.exit_btn.pack(side=tk.LEFT, padx=5)
        self.exit_display = tk.Label(exit_inner, text="Not set",
                                    bg='#1e1e1e', fg='#a060d0', font=('Arial', 11, 'bold'))
        self.exit_display.pack(side=tk.LEFT, padx=5)

        totems_frame = ttk.Frame(notebook)
        notebook.add(totems_frame, text=" Totems/Items")
        
        totems_content = ttk.LabelFrame(totems_frame, text="Configure Your Items", padding=15)
        totems_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
   
        first_inner = ttk.Frame(totems_content)
        first_inner.pack(fill=tk.X, pady=5)
        ttk.Label(first_inner, text="1st Item Key:").pack(side=tk.LEFT, padx=5)
        self.first_entry = ttk.Entry(first_inner, width=10, font=('Arial', 11))
        self.first_entry.insert(0, self.config['totems']['first'])
        self.first_entry.pack(side=tk.LEFT, padx=5)
        
     
        second_inner = ttk.Frame(totems_content)
        second_inner.pack(fill=tk.X, pady=5)
        self.second_var = tk.BooleanVar(value=self.config['totems']['second_enabled'])
        self.second_check = ttk.Checkbutton(second_inner, text="2nd Item Key:",
                                           variable=self.second_var,
                                           command=self.toggle_second)
        self.second_check.pack(side=tk.LEFT, padx=5)
        self.second_entry = ttk.Entry(second_inner, width=10, font=('Arial', 11))
        self.second_entry.insert(0, self.config['totems']['second'])
        self.second_entry.pack(side=tk.LEFT, padx=5)
        self.second_entry.config(state=tk.NORMAL if self.second_var.get() else tk.DISABLED)
        
   
        third_inner = ttk.Frame(totems_content)
        third_inner.pack(fill=tk.X, pady=5)
        self.third_var = tk.BooleanVar(value=self.config['totems']['third_enabled'])
        self.third_check = ttk.Checkbutton(third_inner, text="3rd Item Key:",
                                          variable=self.third_var,
                                          command=self.toggle_third)
        self.third_check.pack(side=tk.LEFT, padx=5)
        self.third_entry = ttk.Entry(third_inner, width=10, font=('Arial', 11))
        self.third_entry.insert(0, self.config['totems']['third'])
        self.third_entry.pack(side=tk.LEFT, padx=5)
        self.third_entry.config(state=tk.NORMAL if self.third_var.get() else tk.DISABLED)
        
        
        fourth_inner = ttk.Frame(totems_content)
        fourth_inner.pack(fill=tk.X, pady=5)
        self.fourth_var = tk.BooleanVar(value=self.config['totems']['fourth_enabled'])
        self.fourth_check = ttk.Checkbutton(fourth_inner, text="4th Item Key:",
                                           variable=self.fourth_var,
                                           command=self.toggle_fourth)
        self.fourth_check.pack(side=tk.LEFT, padx=5)
        self.fourth_entry = ttk.Entry(fourth_inner, width=10, font=('Arial', 11))
        self.fourth_entry.insert(0, self.config['totems']['fourth'])
        self.fourth_entry.pack(side=tk.LEFT, padx=5)
        self.fourth_entry.config(state=tk.NORMAL if self.fourth_var.get() else tk.DISABLED)
        
    
        delays_frame = ttk.Frame(notebook)
        notebook.add(delays_frame, text=" Delays")
        
        delays_content = ttk.LabelFrame(delays_frame, text="Configure Timing", padding=15)
        delays_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        
        delay_inner = ttk.Frame(delays_content)
        delay_inner.pack(fill=tk.X, pady=8)
        ttk.Label(delay_inner, text="Detection Delay (sec):").pack(side=tk.LEFT, padx=5)
        self.delay_spinbox = ttk.Spinbox(delay_inner, from_=0.1, to=60, increment=0.1,
                                        width=8, justify=tk.CENTER, font=('Arial', 11))
        delay_value = self.config['delay']
        if isinstance(delay_value, str):
            delay_value = float(delay_value) if delay_value else 0.5
        else:
            delay_value = float(delay_value) if delay_value else 0.5
        self.delay_spinbox.set(delay_value)
        self.delay_spinbox.pack(side=tk.LEFT, padx=5)
        delay_btn = tk.Button(delay_inner, text="Set", 
                            bg='#a060d0', fg='#1e1e1e', width=8, font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2,
                            command=self.set_delay)
        delay_btn.pack(side=tk.LEFT, padx=5)
        
    
        action_delay_inner = ttk.Frame(delays_content)
        action_delay_inner.pack(fill=tk.X, pady=8)
        ttk.Label(action_delay_inner, text="Item Action Delay (sec):").pack(side=tk.LEFT, padx=5)
        self.action_delay_spinbox = ttk.Spinbox(action_delay_inner, from_=0.1, to=60, increment=0.1,
                                               width=8, justify=tk.CENTER, font=('Arial', 11))
        self.action_delay_spinbox.set(self.config.get('action_delay', 1.4))
        self.action_delay_spinbox.pack(side=tk.LEFT, padx=5)
        action_delay_btn = tk.Button(action_delay_inner, text="Set", 
                                    bg='#a060d0', fg='#1e1e1e', width=8, font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2,
                                    command=self.set_action_delay)
        action_delay_btn.pack(side=tk.LEFT, padx=5)
        
     
        cycle_cooldown_inner = ttk.Frame(delays_content)
        cycle_cooldown_inner.pack(fill=tk.X, pady=8)
        ttk.Label(cycle_cooldown_inner, text="Cycle Cooldown (sec):").pack(side=tk.LEFT, padx=5)
        self.cycle_cooldown_spinbox = ttk.Spinbox(cycle_cooldown_inner, from_=1, to=600, increment=1,
                                                  width=8, justify=tk.CENTER, font=('Arial', 11))
        self.cycle_cooldown_spinbox.set(self.config.get('cycle_cooldown', 60.0))
        self.cycle_cooldown_spinbox.pack(side=tk.LEFT, padx=5)
        cycle_cooldown_btn = tk.Button(cycle_cooldown_inner, text="Set", 
                                      bg='#a060d0', fg='#1e1e1e', width=8, font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2,
                                      command=self.set_cycle_cooldown)
        cycle_cooldown_btn.pack(side=tk.LEFT, padx=5)
        
       
        start_cooldown_inner = ttk.Frame(delays_content)
        start_cooldown_inner.pack(fill=tk.X, pady=8)
        ttk.Label(start_cooldown_inner, text="Start Cooldown (sec):").pack(side=tk.LEFT, padx=5)
        self.start_cooldown_spinbox = ttk.Spinbox(start_cooldown_inner, from_=0, to=60, increment=0.1,
                                                  width=8, justify=tk.CENTER, font=('Arial', 11))
        self.start_cooldown_spinbox.set(self.config.get('start_cooldown', 7.0))
        self.start_cooldown_spinbox.pack(side=tk.LEFT, padx=5)
        start_cooldown_btn = tk.Button(start_cooldown_inner, text="Set", 
                                      bg='#a060d0', fg='#1e1e1e', width=8, font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2,
                                      command=self.set_start_cooldown)
        start_cooldown_btn.pack(side=tk.LEFT, padx=5)
        
        
        item_press_delay_inner = ttk.Frame(delays_content)
        item_press_delay_inner.pack(fill=tk.X, pady=8)
        ttk.Label(item_press_delay_inner, text="Item Press Delay (sec):").pack(side=tk.LEFT, padx=5)
        self.item_press_delay_spinbox = ttk.Spinbox(item_press_delay_inner, from_=0, to=5, increment=0.05,
                                                    width=8, justify=tk.CENTER, font=('Arial', 11))
        self.item_press_delay_spinbox.set(self.config.get('item_press_delay', 0.1))
        self.item_press_delay_spinbox.pack(side=tk.LEFT, padx=5)
        item_press_delay_btn = tk.Button(item_press_delay_inner, text="Set", 
                                        bg='#a060d0', fg='#1e1e1e', width=8, font=('Arial', 10, 'bold'), relief=tk.RAISED, bd=2,
                                        command=self.set_item_press_delay)
        item_press_delay_btn.pack(side=tk.LEFT, padx=5)
        
      
        area_frame = ttk.Frame(notebook)
        notebook.add(area_frame, text=" Area Selection")
        
        area_content = ttk.LabelFrame(area_frame, text="Invite Box Position", padding=15)
        area_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
      
        self.select_area_btn = tk.Button(area_content, text="SELECT POSITION", 
                                         bg='#a060d0', fg='#1e1e1e', font=('Arial', 12, 'bold'),
                                         height=2, command=self.open_area_box,
                                         activebackground='#1e1e1e', activeforeground='#a060d0',
                                         relief=tk.RAISED, bd=2, borderwidth=3)
        self.select_area_btn.pack(fill=tk.X, pady=10)
        
        # Area coordinates display
        self.area_coordinates_label = tk.Label(area_content, text="No area selected",
                                              bg='#1e1e1e', fg='#a060d0', font=('Arial', 11))
        self.area_coordinates_label.pack(pady=10)
        
     
        if self.config.get('area'):
            area = self.config['area']
            self.area_coordinates_label.config(
                text=f"Position: ({area['x']}, {area['y']}) | Size: {area['width']}x{area['height']}"
            )
        
     
        if self.keybinds['start']:
            self.fishing_display.config(text=str(self.keybinds['start']))
        if self.keybinds['area']:
            self.area_display.config(text=str(self.keybinds['area']))
        if self.keybinds['exit']:
            self.exit_display.config(text=str(self.keybinds['exit']))
        
        # Fechar
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
    
    def toggle_second(self):
        """Toggle segundo totem"""
        state = tk.NORMAL if self.second_var.get() else tk.DISABLED
        self.second_entry.config(state=state)
    
    def toggle_third(self):
        
        state = tk.NORMAL if self.third_var.get() else tk.DISABLED
        self.third_entry.config(state=state)
    
    def toggle_fourth(self):
    
        state = tk.NORMAL if self.fourth_var.get() else tk.DISABLED
        self.fourth_entry.config(state=state)
    
    def set_keybind(self, keybind_type):
       
        dialog = KeybindDialog(self.root, f"Set {keybind_type.title()} Keybind")
        self.root.wait_window(dialog)
        
        if dialog.key_pressed:
            self.keybinds[keybind_type] = dialog.key_pressed
            self.save_config()
            
            # Atualizar display
            if keybind_type == 'start':
                self.fishing_display.config(text=dialog.key_pressed)
            elif keybind_type == 'area':
                self.area_display.config(text=dialog.key_pressed)
            elif keybind_type == 'exit':
                self.exit_display.config(text=dialog.key_pressed)
            
           
            keyboard.clear_all_hotkeys()
            self.setup_global_keybinds()
    
    def monitor_green_area(self):
      
        try:
            while self.is_running:
             
                try:
                    delay_sec = float(self.delay_spinbox.get())
                    cycle_cooldown_sec = float(self.cycle_cooldown_spinbox.get())
                except:
                    delay_sec = 0.5
                    cycle_cooldown_sec = 60.0
                
             
                area = self.config.get('area')
                if area and all(key in area for key in ['x', 'y', 'width', 'height']):
                    # Detectar presença de verde
                    green_percentage = detect_green_presence(
                        area['x'],
                        area['y'],
                        area['width'],
                        area['height']
                    )
                    
                  
                    if green_percentage > 0.5: 
                        print(f"[✓] Green detected: {green_percentage:.2f}% - Time: {time.strftime('%H:%M:%S')}")
                     
                        self.use_items()
                       
                        print(f"[⏱] Cycle complete. Starting {cycle_cooldown_sec}s cooldown...")
                        time.sleep(cycle_cooldown_sec)
                        print(f"[✓] Cooldown finished. Resuming green detection.")
                    else:
                        print(f"[✗] No green detected: {green_percentage:.2f}% - Time: {time.strftime('%H:%M:%S')}")
                        
                        time.sleep(delay_sec)
                else:
                    print("[!] Area not configured yet")
                    time.sleep(delay_sec)
        except Exception as e:
            print(f"[✗] Error in monitor_green_area: {e}")
    
    def use_items(self):
      
        try:
            print("[*] Using items sequence...")
            
         
            try:
                detection_delay_sec = float(self.delay_spinbox.get())
                action_delay_sec = float(self.action_delay_spinbox.get())
            except:
                detection_delay_sec = 10.0
                action_delay_sec = 1.4
            
          
            if self.keybinds['start']:
                keyboard.press_and_release(self.keybinds['start'].lower())
                print(f"[→] Pressed start keybind: {self.keybinds['start']}")
            
            
            print(f" Waiting {detection_delay_sec}s before using items.")
            time.sleep(detection_delay_sec)
            
        
            items = [
                self.first_entry.get(),
                self.second_entry.get() if self.second_var.get() else None,
                self.third_entry.get() if self.third_var.get() else None,
                self.fourth_entry.get() if self.fourth_var.get() else None,
            ]
            
         
            valid_items = []
            for idx, item in enumerate(items):
                if item and item.strip():
                    valid_items.append(item.strip())
                elif item is not None and (not item or not item.strip()):
                    # Item checkbox marcado mas vazio
                    item_names = ['1st', '2nd', '3rd', '4th']
                    print(f"[!] Warning: {item_names[idx]} item is enabled but empty. Skipping...")
            
            if not valid_items:
                print("No valid items to use. Please configure at least one item.")
                return
            
            print(f"[*] Using {len(valid_items)} item(s): {valid_items}")
            
      
            try:
                item_press_delay_sec = float(self.item_press_delay_spinbox.get())
            except:
                item_press_delay_sec = 0.1
            
            for idx, item_key in enumerate(valid_items):
            
                keyboard.press_and_release(item_key.strip())
                print(f"[→] Pressed item key: {item_key.strip()}")
                
             
                if item_press_delay_sec > 0:
                    time.sleep(item_press_delay_sec)
                    print(f"[⏱] Waited {item_press_delay_sec}s after item key press")
                
              
                pyautogui.click()
                print(f"[→] Clicked at current mouse position")
                
             
                if idx < len(valid_items) - 1:  # Não aguarda após o último item
                    time.sleep(action_delay_sec)
                    print(f"[⏱] Waited {action_delay_sec}s before next item")
            
       
            if self.keybinds['start']:
                keyboard.press_and_release(self.keybinds['start'].lower())
                print(f"[→] Pressed start keybind again: {self.keybinds['start']}")
            
            print("[✓] Items sequence completed")
        except Exception as e:
            print(f"[✗] Error in use_items: {e}")
    
    def toggle_start_stop(self):
        """Toggle start/stop"""
        self.is_running = not self.is_running
        self.save_config()
        
        if self.is_running:
            self.start_stop_btn.config(text="STOP", bg='#ff4444', fg='#a060d0')
            self.start_stop_btn.config(state=tk.DISABLED) 
            messagebox.showinfo("Status", "Macro started! Get ready...")
            
        
            try:
                start_cooldown_sec = float(self.start_cooldown_spinbox.get())
            except:
                start_cooldown_sec = 7.0
            
           
            def start_with_cooldown():
                print(f" Preparation cooldown: {start_cooldown_sec}s")
                time.sleep(start_cooldown_sec)
                print("Cooldown finished. Starting green detection.")
                
                
                thread = threading.Thread(target=self.monitor_green_area, daemon=True)
                thread.start()
                print(" Green detection monitoring started")
                self.start_stop_btn.config(state=tk.NORMAL)  # Reabilita o botão
            
            cooldown_thread = threading.Thread(target=start_with_cooldown, daemon=True)
            cooldown_thread.start()
        else:
            self.start_stop_btn.config(text="START", bg='#2d2d2d', fg='#a060d0')
            self.start_stop_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Status", "Macro stopped!")
            print("[✓] Green detection monitoring stopped")
    
    def set_start_cooldown(self):
     
        start_cooldown_value = self.start_cooldown_spinbox.get()
        self.save_config()
        messagebox.showinfo("Start Cooldown Set", f"Start cooldown set to {start_cooldown_value}s")
    
    def set_item_press_delay(self):
     
        item_press_delay_value = self.item_press_delay_spinbox.get()
        self.save_config()
        messagebox.showinfo("Item Press Delay Set", f"Item press delay set to {item_press_delay_value}s")
    
    def open_area_box(self):
      
        if self.area_window is not None and self.area_window.winfo_exists():
            return
        
        print(" Opening area selector...")
        self.area_window = AreaSelectorWindow(self.root, self.save_area_box,
                                             self.config.get('area'))
    
    def save_area_box(self, area_data):
      
        self.config['area'] = area_data
        self.save_config()
        
    
        self.area_coordinates_label.config(
            text=f"Position: ({area_data['x']}, {area_data['y']}) | Size: {area_data['width']}x{area_data['height']}"
        )
        
        green_percentage = detect_green_presence(
            area_data['x'], 
            area_data['y'], 
            area_data['width'], 
            area_data['height']
        )
        
        messagebox.showinfo("Area Saved", 
                          f"Area saved!\nPosition: ({area_data['x']}, {area_data['y']})\n"
                          f"Size: {area_data['width']}x{area_data['height']}\n"
                          f"Green presence: {green_percentage:.2f}%")
        print("[✓] Area saved")
        print(f"[✓] Green presence: {green_percentage:.2f}%")
    
    def set_delay(self):

        delay_value = self.delay_spinbox.get()
        self.save_config()
        messagebox.showinfo("Detection Delay Set", f"Detection delay set to {delay_value}s")
    
    def set_action_delay(self):
     
        action_delay_value = self.action_delay_spinbox.get()
        self.save_config()
        messagebox.showinfo("Action Delay Set", f"Action delay set to {action_delay_value}s")
    
    def set_cycle_cooldown(self):
    
        cycle_cooldown_value = self.cycle_cooldown_spinbox.get()
        self.save_config()
        messagebox.showinfo("Cycle Cooldown Set", f"Cycle cooldown set to {cycle_cooldown_value}s") 
    
    def setup_global_keybinds(self):
  
        def keybind_listener():
            try:
                
                if self.keybinds['exit']:
                    exit_key = self.keybinds['exit'].lower()
                    def exit_cmd():
                        self.save_config()
                        self.root.quit()
                    keyboard.add_hotkey(exit_key, exit_cmd)
                    print(f"[✓] Exit keybind registered: {exit_key}")
                
                while True:
                    time.sleep(0.1)
            except Exception as e:
                print(f"[✗] Error in keybind_listener: {e}")
        
        thread = threading.Thread(target=keybind_listener, daemon=True)
        thread.start()
    
    def on_closing(self):

        self.save_config()
        self.root.quit()


def main():
    root = tk.Tk()
    app = SomelleAutoTotem(root)
    root.mainloop()


if __name__ == '__main__':
    main()
