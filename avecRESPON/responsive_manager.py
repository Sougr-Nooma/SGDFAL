import tkinter as tk
from tkinter import ttk

class ResponsiveManager:
    """Classe utilitaire pour gérer le responsive design"""
    
    @staticmethod
    def configure_grid(frame, rows_weights=None, cols_weights=None):
        """
        Configure un grid layout responsive
        rows_weights: liste des poids pour chaque ligne (ex: [1, 2, 1])
        cols_weights: liste des poids pour chaque colonne
        """
        if rows_weights:
            for i, weight in enumerate(rows_weights):
                frame.grid_rowconfigure(i, weight=weight)
        if cols_weights:
            for i, weight in enumerate(cols_weights):
                frame.grid_columnconfigure(i, weight=weight)
    
    @staticmethod
    def make_scrollable(parent):
        """Crée un système de scroll responsive"""
        # Canvas pour le défilement
        canvas = tk.Canvas(parent, bg="white")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        
        # Frame scrollable
        scrollable_frame = tk.Frame(canvas, bg="white")
        
        # Lier le frame au canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Gestion du redimensionnement
        def on_canvas_configure(event):
            canvas_width = event.width
            canvas.itemconfig("all", width=canvas_width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        
        return canvas, scrollbar, scrollable_frame
    
    @staticmethod
    def get_font_sizes(width):
        """Retourne les tailles de police adaptées à la largeur"""
        if width < 900:
            return {"title": 12, "subtitle": 10, "normal": 9, "card_title": 10, "card_value": 12}
        elif width < 1200:
            return {"title": 14, "subtitle": 12, "normal": 10, "card_title": 11, "card_value": 14}
        else:
            return {"title": 16, "subtitle": 14, "normal": 11, "card_title": 12, "card_value": 16}