import sys
import tkinter as tk
from tkinter.filedialog import askdirectory

root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)

dir = askdirectory(
    initialdir=sys.argv[1],
    parent=root,
    mustexist=True
)

root.destroy()
print(dir)
