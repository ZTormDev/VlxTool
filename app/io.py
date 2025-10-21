from tkinter import Tk, filedialog


def prompt_for_hpp_file():
    root = Tk(); root.withdraw()
    path = filedialog.askopenfilename(
        title="Select BlockTypes.hpp",
        filetypes=(("C++ Header", "*.hpp"), ("All files", "*.*"))
    )
    root.destroy()
    return path
