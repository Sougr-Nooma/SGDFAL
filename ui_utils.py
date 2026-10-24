import os
import sys
import tkinter as tk
from pathlib import Path

COULEURS_FOND_LOGO = {
    "accueil": "#E6EFF7",
    "revenus": "#E5F2E8",
    "depenses": "#F8E6E2",
    "rapport": "#ECE7F5",
    "comptes": "#E6EFF7",
    "parametres": "#ECE7F5",
    "securite": "#F3E5F5",
}


def resource_path(relative_path):
    """Retourne le chemin d'une ressource en développement ou dans PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return os.path.join(base_path, relative_path)


def creer_logo_section(section, size=32):
    """Compose le logo transparent sur un fond clair adapté à la section."""
    from PIL import Image

    couleur = COULEURS_FOND_LOGO.get(section, COULEURS_FOND_LOGO["accueil"])
    logo = Image.open(resource_path("SGD.png")).convert("RGBA")
    logo = logo.resize((size, size), Image.Resampling.LANCZOS)
    fond = Image.new("RGBA", (size, size), couleur)
    fond.alpha_composite(logo)
    return fond


def centrer_fenetre(window, width, height, parent=None):
    """Centre une fenêtre à l'écran ou dans une fenêtre parente visible."""
    window.update_idletasks()
    if parent is None:
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
    else:
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def placer_fenetre_sous_navbar(window, parent, width, height):
    """Place une fenêtre juste sous la barre de navigation visible."""
    root = parent.winfo_toplevel()
    navbar = getattr(root, "_sgd_navbar", None)
    window.update_idletasks()
    if navbar is None or root.state() == "withdrawn":
        centrer_fenetre(window, width, height, parent)
        return

    root.update_idletasks()
    navbar.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - width) // 2
    y = navbar.winfo_rooty() + navbar.winfo_height()
    window.geometry(f"{width}x{height}+{x}+{y}")


def configurer_icone_fenetre(root, section=None):
    """Applique une icône SGD accordée à la fenêtre sans remplacer la navbar."""
    try:
        if section:
            from PIL import ImageTk

            image = creer_logo_section(section)
            root._sgd_icon_photo = ImageTk.PhotoImage(image)
            root.iconphoto(False, root._sgd_icon_photo)
        else:
            root._sgd_icon_photo = tk.PhotoImage(file=resource_path("SGD.png"))
            root.iconphoto(True, root._sgd_icon_photo)
    except (ImportError, OSError, tk.TclError):
        try:
            root.iconbitmap(resource_path("SGD.ico"))
        except tk.TclError as erreur:
            print(f"Impossible de charger l'icône SGD : {erreur}")
