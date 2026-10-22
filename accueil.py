import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
from database import get_total_depenses, get_total_depenses_pour_periode, get_dernieres_depenses, get_revenus_pour_periode
import datetime
import sqlite3
import database

class Accueil:
    def __init__(self, parent_frame, compte_actif):
        self.parent_frame = parent_frame
        self.compte_actif = compte_actif

    def afficher(self):
        """Affiche le dashboard complet de l'onglet Accueil"""
        # Effacer tout contenu existant
        for widget in self.parent_frame.winfo_children():
            widget.destroy()
        
        # === Créer un conteneur scrollable ===
        scroll_canvas = tk.Canvas(self.parent_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.parent_frame, orient="vertical", command=scroll_canvas.yview)
        
        # Frame scrollable principal
        scrollable_frame = tk.Frame(scroll_canvas, bg="white")
        
        # Configurer le canvas pour qu'il suive la taille de la fenêtre
        def configure_scroll_region(event=None):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        
        # Créer une fenêtre dans le canvas qui s'étend sur toute la largeur
        canvas_window = scroll_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Fonction pour redimensionner le frame intérieur avec la largeur du canvas
        def configure_canvas_width(event):
            canvas_width = event.width
            scroll_canvas.itemconfig(canvas_window, width=canvas_width)
        
        scroll_canvas.bind("<Configure>", configure_canvas_width)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configurer la liaison de la roulette de la souris
        def _on_mousewheel(event):
            scroll_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        
        scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows
        scroll_canvas.bind_all("<Button-4>", lambda e: scroll_canvas.yview_scroll(-1, "units"))  # Linux
        scroll_canvas.bind_all("<Button-5>", lambda e: scroll_canvas.yview_scroll(1, "units"))   # Linux
        
        # === Positionner Canvas et Scrollbar ===
        scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configurer la grille du frame scrollable pour le centrage
        scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # === Titre principal ===
        current_date = datetime.datetime.now().strftime("%d/%m/%Y")
        title_frame = tk.Frame(scrollable_frame, bg="white")
        title_frame.grid(row=0, column=0, sticky="ew", pady=15, padx=20)
        title_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(title_frame, 
            text=f"📊 Vue d'ensemble de vos finances à la date du: {current_date}", 
            font=("Arial", 18, "bold"), 
            bg="white", fg="#2c3e50"
        ).grid(row=0, column=0)
        
        # === Conteneur pour les 4 cartes ===
        cards_container = tk.Frame(scrollable_frame, bg="white")
        cards_container.grid(row=1, column=0, sticky="ew", pady=10, padx=20)
        
        # Configurer la grille pour distribuer équitablement les cartes
        for i in range(4):
            cards_container.grid_columnconfigure(i, weight=1, uniform="cards")
        
        # Récupérer les données
        total_depenses = get_total_depenses(self.compte_actif)
        total_revenus = self.get_total_revenus()
        revenu_net = total_revenus - total_depenses
        benefice = revenu_net
        
        # === Carte 1 : Revenus totaux ===
        card1 = tk.Frame(cards_container, bg="#e8f5e9", relief="raised", bd=2, padx=15, pady=15)
        card1.grid(row=0, column=0, padx=5, sticky="nsew")
        tk.Label(card1, text="💰 Revenus totaux", font=("Arial", 11, "bold"), bg="#e8f5e9", fg="#2e7d32").pack()
        tk.Label(card1, text=f"{total_revenus:.2f} TND", font=("Arial", 16, "bold"), bg="#e8f5e9", fg="#1b5e20").pack()
        
        # === Carte 2 : Dépenses totales ===
        card2 = tk.Frame(cards_container, bg="#ffebee", relief="raised", bd=2, padx=15, pady=15)
        card2.grid(row=0, column=1, padx=5, sticky="nsew")
        tk.Label(card2, text="💸 Dépenses totales", font=("Arial", 11, "bold"), bg="#ffebee", fg="#c62828").pack()
        tk.Label(card2, text=f"{total_depenses:.2f} TND", font=("Arial", 16, "bold"), bg="#ffebee", fg="#b71c1c").pack()
        
        # === Carte 3 : Revenu net ===
        card3 = tk.Frame(cards_container, bg="#e3f2fd", relief="raised", bd=2, padx=15, pady=15)
        card3.grid(row=0, column=2, padx=5, sticky="nsew")
        tk.Label(card3, text="📈 Revenu net", font=("Arial", 11, "bold"), bg="#e3f2fd", fg="#1565c0").pack()
        color = "#1565c0" if revenu_net >= 0 else "#c62828"
        tk.Label(card3, text=f"{revenu_net:.2f} TND", font=("Arial", 16, "bold"), bg="#e3f2fd", fg=color).pack()
        
        # === Carte 4 : Bénéfice estimé ===
        card4 = tk.Frame(cards_container, bg="#f0f4c3", relief="raised", bd=2, padx=15, pady=15)
        card4.grid(row=0, column=3, padx=5, sticky="nsew")
        tk.Label(card4, text="✅ Bénéfice estimé", font=("Arial", 11, "bold"), bg="#f0f4c3", fg="#558b2f").pack()
        color = "#558b2f" if benefice >= 0 else "#c62828"
        tk.Label(card4, text=f"{benefice:.2f} TND", font=("Arial", 16, "bold"), bg="#f0f4c3", fg=color).pack()
        
        # === Conteneur pour le graphique ===
        graph_container = tk.Frame(scrollable_frame, bg="white")
        graph_container.grid(row=2, column=0, sticky="ew", pady=20, padx=20)
        graph_container.grid_columnconfigure(0, weight=1)
        
        # === Graphique en barres : 6 derniers mois ===
        data = self.get_finances_par_mois(6)
        if data:
            fig, ax = plt.subplots(figsize=(10, 5))
            months = [item[0] for item in data]
            revenues = [item[1] for item in data]
            expenses = [item[2] for item in data]
            
            # Barres côte à côte
            x = range(len(months))
            width = 0.35
            
            bars_revenues = ax.bar([i - width/2 for i in x], revenues, width, 
                                label="Revenus", color="#2ecc71", alpha=0.8)
            bars_expenses = ax.bar([i + width/2 for i in x], expenses, width, 
                                label="Dépenses", color="#e74c3c", alpha=0.8)
            
            # Labels et titre
            ax.set_xlabel("Mois", fontsize=11)
            ax.set_ylabel("Montant (TND)", fontsize=11)
            ax.set_title("Évolution des revenus et dépenses (6 derniers mois)", fontsize=13, pad=15)
            ax.set_xticks(x)
            ax.set_xticklabels(months, rotation=45, ha='right', fontsize=9)
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            # Ajouter les valeurs sur les barres
            max_value = max(max(revenues) if revenues else 0, max(expenses) if expenses else 0)
            for bar in bars_revenues:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + max_value*0.01,
                        f'{height:.0f}', ha='center', va='bottom', fontsize=8)
            
            for bar in bars_expenses:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + max_value*0.01,
                        f'{height:.0f}', ha='center', va='bottom', fontsize=8)
            
            plt.tight_layout()
            
            graph_canvas = FigureCanvasTkAgg(fig, master=graph_container)
            graph_canvas.draw()
            graph_canvas.get_tk_widget().grid(row=0, column=0, sticky="ew")
        
        # === Conteneur pour les dernières dépenses ===
        expenses_container = tk.Frame(scrollable_frame, bg="white")
        expenses_container.grid(row=3, column=0, sticky="ew", pady=(10, 20), padx=20)
        expenses_container.grid_columnconfigure(0, weight=1)
        
        tk.Label(expenses_container, 
            text="🕒 Dernières dépenses", 
            font=("Arial", 14, "bold"), 
            bg="white", fg="#2c3e50"
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Treeview pour les dépenses
        tree_frame = tk.Frame(expenses_container, bg="white")
        tree_frame.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_columnconfigure(0, weight=1)
        
        tree = ttk.Treeview(tree_frame, 
            columns=("Date", "Montant", "Catégorie", "Description"), 
            show="headings", 
            height=5
        )
        tree.heading("Date", text="Date")
        tree.heading("Montant", text="Montant (TND)")
        tree.heading("Catégorie", text="Catégorie")
        tree.heading("Description", text="Description")
        tree.column("Date", width=100, anchor="center")
        tree.column("Montant", width=100, anchor="center")
        tree.column("Catégorie", width=120, anchor="center")
        tree.column("Description", width=250, anchor="w")
        tree.grid(row=0, column=0, sticky="ew")
        
        # Scrollbar pour le treeview
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=tree_scrollbar.set)
        
        dernieres_depenses = get_dernieres_depenses(self.compte_actif, 5)
        for dep in dernieres_depenses:
            tree.insert("", "end", values=(dep[0], f"{dep[1]:.2f}", dep[2], dep[3] or "-"))
        
        # === Configuration finale ===
        scrollable_frame.update_idletasks()
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
    
    def get_total_revenus(self):
        """Renvoie le total des revenus du compte actif"""
        conn = database.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(montant) FROM revenus WHERE compte = ?", (self.compte_actif,))
        result = cursor.fetchone()[0]
        conn.close()
        return result if result else 0.0
    
    def get_finances_par_mois(self, nb_mois=6):
        """Renvoie les revenus et dépenses totaux pour les N derniers mois"""
        today = datetime.datetime.now()
        result = []
        for i in range(nb_mois):
            month = today.month - i
            year = today.year
            if month <= 0:
                month += 12
                year -= 1
            # Calculer la date de début et fin du mois
            start = datetime.datetime(year, month, 1)
            if month == 12:
                end = datetime.datetime(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end = datetime.datetime(year, month + 1, 1) - datetime.timedelta(days=1)
            # Formater le nom du mois
            month_name = start.strftime("%B %Y")
            # Revenus du mois
            revenus = get_revenus_pour_periode(self.compte_actif, start, end)
            # Dépenses du mois
            depenses = get_total_depenses_pour_periode(self.compte_actif, start, end)
            result.append((month_name, revenus, depenses))
        return result[::-1]  # Inverser pour avoir les plus récents à la fin