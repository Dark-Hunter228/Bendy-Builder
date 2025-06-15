import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import shutil
import subprocess

window_width = 675
window_height = 450

image_height = int(window_height * 0.7)
bottom_height = window_height - image_height

root = tk.Tk()
root.title("Bendy Builder Installer")
root.resizable(False, False)

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{x}+{y}")

root.configure(bg="black")

top_frame = tk.Frame(root, width=window_width, height=image_height, bg="black", highlightthickness=0, bd=0)
top_frame.pack(side="top", fill="both", expand=False)

try:
    img = Image.open("splash.jpg")
    img = img.resize((window_width, image_height), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(img)

    image_label = tk.Label(top_frame, image=photo, borderwidth=0, highlightthickness=0)
    image_label.image = photo
    image_label.pack(fill="both", expand=True)
except Exception as e:
    error_label = tk.Label(top_frame, text=f"Ошибка загрузки splash.jpg:\n{e}", fg="red", bg="black")
    error_label.pack(pady=10)

bottom_panel = tk.Frame(root, bg="black", height=bottom_height, highlightthickness=0, bd=0)
bottom_panel.pack(side="bottom", fill="x")

install_button = tk.Button(
    bottom_panel,
    text="Установить",
    bg="#222222",
    fg="white",
    activebackground="#444444",
    activeforeground="white",
    font=("Segoe UI", 18, "bold"),
    bd=0,
    relief="flat",
    padx=30,
    pady=15,
    cursor="hand2"
)
install_button.pack(expand=True)


def create_shortcut_powershell(target_path, shortcut_path, working_dir=None, icon=None):
    target_path = target_path.replace("\\", "\\\\")
    shortcut_path = shortcut_path.replace("\\", "\\\\")
    
    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target_path}"
'''
    if working_dir:
        working_dir_esc = working_dir.replace("\\", "\\\\")
        ps_script += f'$Shortcut.WorkingDirectory = "{working_dir_esc}"\n'
    if icon:
        icon_esc = icon.replace("\\", "\\\\")
        ps_script += f'$Shortcut.IconLocation = "{icon_esc}"\n'
    
    ps_script += '$Shortcut.Save()\n'
    
    try:
        subprocess.run(["powershell", "-Command", ps_script], check=True)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Ошибка", f"Не удалось создать ярлык:\n{e}")


def extract_rar_with_winrar_local(rar_path, extract_to):
    winrar_exe = os.path.join(os.path.dirname(__file__), 'WinRAR', 'WinRAR.exe')
    if not os.path.exists(winrar_exe):
        raise FileNotFoundError(f"WinRAR.exe не найден по пути {winrar_exe}")

    os.makedirs(extract_to, exist_ok=True)
    command = [winrar_exe, 'x', '-y', rar_path, extract_to]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка распаковки архива:\n{result.stderr}")


def install():
    try:
        rar_path = os.path.abspath("Files.rar")
        extract_path = os.path.abspath("Files")

        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        os.makedirs(extract_path, exist_ok=True)

        extract_rar_with_winrar_local(rar_path, extract_path)

        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        install_dir = os.path.join(program_files, "BendyBuilder")

        if os.path.exists(install_dir):
            shutil.rmtree(install_dir)

        shutil.copytree(extract_path, install_dir)

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        target_exe = os.path.join(install_dir, "BendyBuilder.exe")
        shortcut_path = os.path.join(desktop, "BendyBuilder.lnk")

        create_shortcut_powershell(target_exe, shortcut_path, working_dir=install_dir, icon=target_exe)

        messagebox.showinfo("Установка", "Установка завершена. Установщик будет закрыт.")
        root.destroy()

    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при установке:\n{e}")


install_button.config(command=install)

root.mainloop()
