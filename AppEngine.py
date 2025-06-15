import tkinter as tk
from tkinter import filedialog, Menu, simpledialog
from PIL import Image, ImageTk
import os
import json

SPRITE_DIR = "sprites"
FIXED_SIZES = {
    "Пол": (300, 300),
    "Стена": (670, 670),
    "Клякса": (250, 250),
    "Картонка Бенди": (200, 300),
    "Дверь": (200, 300)
}

try:
    RESAMPLING = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING = Image.ANTIALIAS


class BendyBuilder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bendy Builder RC3")
        self.state('zoomed')

        self.canvas = tk.Canvas(self, bg="#e0e0e0")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.bottom_panel = tk.Frame(self, height=30, bg="white")
        self.bottom_panel.pack(fill="x", side="bottom")

        self.tool_mode = tk.StringVar(value="standard")
        self.project_name = "MyProject"
        self.scene_index = 0
        self.scenes = {0: []}
        self.current_scene = self.scenes[0]
        self.custom_sprite_paths = {}

        self.setup_toolbar()
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        self.objects_menu = self.create_objects_menu()
        self.setup_menus()

        self.sprites = {}
        self.objects = []
        self.player = None
        self.dragging = None
        self.offset = (0, 0)
        self.context_menu = None
        self.rotation_buttons = []

        self.selected_object = None
        self.selection_rect = None

        self.load_sprites()
        self.bind_events()
        self.update_game()

    def setup_toolbar(self):
        tk.Button(self.bottom_panel, text="Макеты", command=self.show_scene_menu).pack(side="left", padx=5)
        tk.Button(self.bottom_panel, text="Вращение", command=self.set_rotate_mode).pack(side="right", padx=5)
        tk.Button(self.bottom_panel, text="Стандарт", command=self.set_standard_mode).pack(side="right", padx=5)

    def set_standard_mode(self):
        self.tool_mode.set("standard")
        self.remove_rotation_buttons()

    def set_rotate_mode(self):
        self.tool_mode.set("rotate")

    def setup_menus(self):
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Save", command=self.save_project)
        file_menu.add_command(label="Open", command=self.open_project)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        edit_menu.add_command(label="Settings Project", command=self.project_settings)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)

        self.menu_bar.add_cascade(label="Objects", menu=self.objects_menu)

    def create_objects_menu(self):
        obj_menu = tk.Menu(self.menu_bar, tearoff=0)
        items = ["Пол", "Стена", "Клякса", "Сломанная стена", "Дверь", "Картонка Бенди", "---", "Игрок", "---", "Триггер сцены", "Добавить собственный спрайт"]
        for name in items:
            if name == "---":
                obj_menu.add_separator()
            elif name == "Добавить собственный спрайт":
                obj_menu.add_command(label=name, command=self.add_custom_sprite)
            else:
                obj_menu.add_command(label=name, command=lambda n=name: self.add_object(n))
        return obj_menu

    def add_custom_sprite(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if path:
            name = os.path.basename(path)
            image = Image.open(path)
            self.sprites[name] = image
            self.custom_sprite_paths[name] = path
            self.objects_menu.add_command(label=name, command=lambda n=name: self.add_object(n))

    def project_settings(self):
        name = simpledialog.askstring("Project Settings", "Введите название проекта:", initialvalue=self.project_name)
        if name:
            self.project_name = name

    def load_sprites(self):
        files = {
            "Пол": "Floor.png",
            "Стена": "Wall.png",
            "Клякса": "ink.png",
            "Сломанная стена": "Broken.png",
            "Дверь": "Door.png",
            "Картонка Бенди": "Bendy.png",
            "Игрок": "Player.png",
            "Триггер сцены": "TriggerScene.png"
        }
        for name, file in files.items():
            path = os.path.join(SPRITE_DIR, file)
            image = Image.open(path)
            if name in FIXED_SIZES:
                image = image.resize(FIXED_SIZES[name], RESAMPLING)
            self.sprites[name] = image

    def add_object(self, name):
        if name == "Игрок" and self.player:
            return
        if name == "Триггер сцены":
            index = simpledialog.askinteger("Индекс сцены", "Индекс переключаемого макета:", initialvalue=0)
            if index is None:
                return
        else:
            index = None

        pil_image = self.sprites[name]
        tk_image = ImageTk.PhotoImage(pil_image)
        obj = {
            "name": name,
            "image": pil_image,
            "tk": tk_image,
            "x": 100,
            "y": 100,
            "angle": 0,
            "id": self.canvas.create_image(100, 100, image=tk_image, anchor="nw"),
            "vel_y": 0,
            "target_scene": index
        }
        self.objects.append(obj)
        if name == "Игрок":
            self.player = obj
        if name == "Триггер сцены":
            self.canvas.tag_raise(obj["id"])

    def show_scene_menu(self):
        menu = Menu(self, tearoff=0)
        for idx in sorted(self.scenes):
            menu.add_command(label=f"Макет{idx:02}", command=lambda i=idx: self.switch_scene(i))
        menu.add_command(label="Добавить макет", command=self.add_scene)
        menu.post(self.winfo_pointerx(), self.winfo_pointery())

    def add_scene(self):
        new_index = max(self.scenes.keys()) + 1
        self.scenes[new_index] = []
        self.switch_scene(new_index)

    def switch_scene(self, index):
        self.save_current_scene()
        self.canvas.delete("all")
        self.objects.clear()
        self.player = None
        self.remove_selection()
        self.scene_index = index
        self.current_scene = self.scenes[index]
        for obj_data in self.current_scene:
            name = obj_data["name"]
            image = self.sprites.get(name)
            if not image and name in self.custom_sprite_paths:
                image = Image.open(self.custom_sprite_paths[name])
            angle = obj_data.get("angle", 0)
            rotated = image.rotate(-angle, resample=Image.BICUBIC, expand=True)
            tk_image = ImageTk.PhotoImage(rotated)
            obj = {
                **obj_data,
                "angle": angle,
                "image": image,
                "tk": tk_image,
                "id": self.canvas.create_image(obj_data["x"], obj_data["y"], image=tk_image, anchor="nw")
            }
            self.objects.append(obj)
            if name == "Игрок":
                self.player = obj

    def save_current_scene(self):
        self.current_scene.clear()
        for obj in self.objects:
            self.current_scene.append({
                "name": obj["name"],
                "x": obj["x"],
                "y": obj["y"],
                "angle": obj.get("angle", 0),
                "target_scene": obj.get("target_scene", None)
            })

    def bind_events(self):
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Left>", lambda e: self.move_player(-5))
        self.bind("<Right>", lambda e: self.move_player(5))

        # Копировать/вставить
        self.bind_all("<Control-c>", self.copy_object)
        self.bind_all("<Control-C>", self.copy_object)
        self.bind_all("<Control-v>", self.paste_object)
        self.bind_all("<Control-V>", self.paste_object)

    def on_click(self, event):
        self.canvas.focus_set()
        self.close_context_menu()
        self.remove_rotation_buttons()

        for obj in reversed(self.objects):
            if self.object_hit(obj, event.x, event.y):
                self.select_object(obj)
                if self.tool_mode.get() == "rotate":
                    self.show_rotation_buttons(obj)
                    return
                elif obj != self.player:
                    self.dragging = obj
                    self.offset = (event.x - obj["x"], event.y - obj["y"])
                    return

    def on_right_click(self, event):
        self.close_context_menu()
        self.remove_rotation_buttons()

        for obj in reversed(self.objects):
            if self.object_hit(obj, event.x, event.y):
                menu = Menu(self, tearoff=0)
                menu.add_command(label="Удалить", command=lambda: self.delete_object(obj))
                menu.add_command(label="На передний план", command=lambda: self.raise_object(obj))
                menu.add_command(label="На задний план", command=lambda: self.lower_object(obj))
                self.context_menu = menu
                menu.post(event.x_root, event.y_root)
                return
        self.context_menu = self.create_objects_menu()
        self.context_menu.post(event.x_root, event.y_root)

    def object_hit(self, obj, x, y):
        ox, oy = obj["x"], obj["y"]
        w, h = obj["tk"].width(), obj["tk"].height()
        return ox <= x <= ox + w and oy <= y <= oy + h

    def delete_object(self, obj):
        self.canvas.delete(obj["id"])
        self.objects.remove(obj)
        if obj == self.player:
            self.player = None
        self.remove_rotation_buttons()
        self.remove_selection()

    def close_context_menu(self):
        if self.context_menu:
            self.context_menu.unpost()
            self.context_menu = None

    def on_drag(self, event):
        if self.tool_mode.get() != "standard":
            return
        if self.dragging:
            self.dragging["x"] = event.x - self.offset[0]
            self.dragging["y"] = event.y - self.offset[1]
            self.canvas.coords(self.dragging["id"], self.dragging["x"], self.dragging["y"])
            self.update_selection_rect()

    def on_release(self, event):
        self.dragging = None
        self.remove_selection()

    def move_player(self, dx):
        if self.player:
            self.player["x"] += dx
            self.canvas.coords(self.player["id"], self.player["x"], self.player["y"])

    def update_game(self):
        if self.player:
            self.player["vel_y"] += 1
            self.player["y"] += self.player["vel_y"]
            for obj in self.objects:
                if obj["name"] == "Пол" and self.check_collision(self.player, obj):
                    self.player["y"] = obj["y"] - self.player["tk"].height()
                    self.player["vel_y"] = 0
                    break
            self.canvas.coords(self.player["id"], self.player["x"], self.player["y"])

            for obj in self.objects:
                if obj["name"] == "Триггер сцены" and self.check_collision(self.player, obj):
                    index = obj.get("target_scene")
                    if index in self.scenes:
                        self.switch_scene(index)

        self.after(20, self.update_game)

    def check_collision(self, a, b):
        ax1, ay1 = a["x"], a["y"]
        ax2, ay2 = ax1 + a["tk"].width(), ay1 + a["tk"].height()
        bx1, by1 = b["x"], b["y"]
        bx2, by2 = bx1 + b["tk"].width(), by1 + b["tk"].height()
        return ax1 < bx2 and ax2 > bx1 and ay2 >= by1 and ay1 < by2

    def rotate_object(self, obj, angle_delta):
        obj["angle"] = (obj["angle"] + angle_delta) % 360
        original_image = self.sprites[obj["name"]]
        rotated = original_image.rotate(-obj["angle"], resample=Image.BICUBIC, expand=True)
        obj["image"] = original_image
        obj["tk"] = ImageTk.PhotoImage(rotated)
        self.canvas.itemconfig(obj["id"], image=obj["tk"])
        self.canvas.coords(obj["id"], obj["x"], obj["y"])
        self.update_selection_rect()

    def show_rotation_buttons(self, obj):
        x, y = obj["x"], obj["y"]
        b1 = tk.Button(self.canvas, text="В", command=lambda: self.rotate_object(obj, 15))
        b2 = tk.Button(self.canvas, text="Н", command=lambda: self.rotate_object(obj, -15))
        b1_window = self.canvas.create_window(x + obj["tk"].width() + 5, y, window=b1)
        b2_window = self.canvas.create_window(x + obj["tk"].width() + 35, y, window=b2)
        self.rotation_buttons = [b1, b2, b1_window, b2_window]

    def remove_rotation_buttons(self):
        for item in self.rotation_buttons:
            if isinstance(item, int):
                self.canvas.delete(item)
            else:
                item.destroy()
        self.rotation_buttons.clear()

    def select_object(self, obj):
        self.remove_selection()
        self.selected_object = obj
        self.update_selection_rect()

    def update_selection_rect(self):
        if self.selected_object:
            obj = self.selected_object
            x, y = obj["x"], obj["y"]
            w, h = obj["tk"].width(), obj["tk"].height()
            if self.selection_rect:
                self.canvas.coords(self.selection_rect, x, y, x + w, y + h)
            else:
                self.selection_rect = self.canvas.create_rectangle(x, y, x + w, y + h, outline="red", width=2)

    def remove_selection(self):
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
        self.selected_object = None

    def raise_object(self, obj):
        self.canvas.tag_raise(obj["id"])
        if self.selection_rect:
            self.canvas.tag_raise(self.selection_rect)

    def lower_object(self, obj):
        self.canvas.tag_lower(obj["id"])

    def copy_object(self, event=None):
        if self.selected_object:
            self.clipboard_object = {
                k: v for k, v in self.selected_object.items()
                if k in ["name", "x", "y", "angle", "target_scene"]
            }

    def paste_object(self, event=None):
        if hasattr(self, 'clipboard_object'):
            data = self.clipboard_object.copy()
            data["x"] += 20
            data["y"] += 20
            name = data["name"]
            image = self.sprites[name]
            rotated = image.rotate(-data.get("angle", 0), resample=Image.BICUBIC, expand=True)
            tk_image = ImageTk.PhotoImage(rotated)
            obj = {
                "name": name,
                "image": image,
                "tk": tk_image,
                "x": data["x"],
                "y": data["y"],
                "angle": data.get("angle", 0),
                "id": self.canvas.create_image(data["x"], data["y"], image=tk_image, anchor="nw"),
                "vel_y": 0,
                "target_scene": data.get("target_scene", None)
            }
            self.objects.append(obj)
            self.select_object(obj)

    def save_project(self):
        self.save_current_scene()
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if not path:
            return
        data = {
            "project_name": self.project_name,
            "scenes": self.scenes,
            "custom_sprite_paths": self.custom_sprite_paths
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not path:
            return
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.project_name = data.get("project_name", "MyProject")
        self.custom_sprite_paths = data.get("custom_sprite_paths", {})
        self.scenes = {int(k): v for k, v in data.get("scenes", {}).items()}
        for name, path in self.custom_sprite_paths.items():
            if name not in self.sprites:
                image = Image.open(path)
                self.sprites[name] = image
        self.switch_scene(min(self.scenes))


if __name__ == "__main__":
    app = BendyBuilder()
    app.mainloop()
