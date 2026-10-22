import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import database
from database import get_total_depenses, get_total_depenses_pour_periode, get_dernieres_depenses, get_revenus_pour_periode
from responsive_manager import ResponsiveManager

class ResponsiveAccueil:
    def __init__(self, parent_frame, compte_actif):
        self.parent_frame = parent_frame
        self.compte_actif = compte_actif
        self.font_sizes = ResponsiveManager.get_font_sizes(1000)  # Taille par défaut

    def update_font_sizes(self, width):
        """Met à jour les tailles de police"""
        self.font_sizes = ResponsiveManager.get_font_sizes(width)

    def afficher(self):
        """Version responsive de l'affichage Accueil"""
        # Effacer le contenu existant
        for widget in self.parent_frame.winfo_children():
            widget.destroy()

        # Configuration grid responsive pour le parent
        ResponsiveManager.configure_grid(self.parent_frame, [0, 0, 1, 0], [1])

        # === TITRE ===
        title_frame = tk.Frame(self.parent_frame, bg="white")
        title_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        title_frame.grid_columnconfigure(0, weight=1)

        current_date = datetime.datetime.now().strftime("%d/%m/%Y")
        title_label = tk.Label(
            title_frame,
            text=f"📊 Vue d'ensemble - {current_date}",
            font=("Arial", self.font_sizes["title"], "bold"),
            bg="white", fg="#2c3e50", wraplength=400
        )
        title_label.grid(row=0, column=0, sticky="w")

        # === CARTES RESPONSIVES ===
        self.create_responsive_cards()

        # === GRAPHIQUE RESPONSIVE ===
        self.create_responsive_graph()

        # === DERNIÈRES DÉPENSES ===
        self.create_responsive_table()

    def create_responsive_cards(self):
        """Crée les cartes de statistiques responsives"""
        cards_frame = tk.Frame(self.parent_frame, bg="white")
        cards_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        # Configuration grid 2x2 pour les cartes
        ResponsiveManager.configure_grid(cards_frame, [1, 1], [1, 1])

        # Récupérer les données
        total_depenses = get_total_depenses(self.compte_actif)
        total_revenus = self.get_total_revenus()
        revenu_net = total_revenus - total_depenses

        # Données des cartes
        cards_data = [
            ("💰 Revenus", f"{total_revenus:.2f} TND", "#e8f5e9", "#2e7d32", 0, 0),
            ("💸 Dépenses", f"{total_depenses:.2f} TND", "#ffebee", "#c62828", 0, 1),
            ("📈 Revenu net", f"{revenu_net:.2f} TND", "#e3f2fd", "#1565c0", 1, 0),
            ("✅ Bénéfice", f"{revenu_net:.2f} TND", "#f0f4c3", "#558b2f", 1, 1)
        ]

        for title, value, bg_color, fg_color, row, col in cards_data:
            card = self.create_card(cards_frame, title, value, bg_color, fg_color)
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

    def create_card(self, parent, title, value, bg_color, fg_color):
        """Crée une carte responsive individuelle"""
        card = tk.Frame(parent, bg=bg_color, relief="raised", bd=1, padx=10, pady=10)
        
        ResponsiveManager.configure_grid(card, [1, 1], [1])
        
        # Titre
        title_label = tk.Label(
            card, text=title, 
            font=("Arial", self.font_sizes["card_title"], "bold"),
            bg=bg_color, fg=fg_color, wraplength=100
        )
        title_label.grid(row=0, column=0, pady=(0, 5))
        
        # Valeur
        value_label = tk.Label(
            card, text=value,
            font=("Arial", self.font_sizes["card_value"], "bold"),
            bg=bg_color, fg=fg_color
        )
        value_label.grid(row=1, column=0)
        
        return card

    def create_responsive_graph(self):
        """Crée le graphique responsive"""
        graph_frame = tk.Frame(self.parent_frame, bg="white")
        graph_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        ResponsiveManager.configure_grid(graph_frame, [1], [1])

        data = self.get_finances_par_mois(6)
        if not data:
            return

        # Taille du graphique adaptative
        fig, ax = plt.subplots(figsize=(10, 4))
        
        months = [item[0] for item in data]
        revenues = [item[1] for item in data]
        expenses = [item[2] for item in data]

        x = range(len(months))
        width = 0.35

        bars_revenues = ax.bar([i - width/2 for i in x], revenues, width, 
                              label="Revenus", color="#2ecc71", alpha=0.8)
        bars_expenses = ax.bar([i + width/2 for i in x], expenses, width, 
                              label="Dépenses", color="#e74c3c", alpha=0.8)

        # Configuration responsive des textes
        ax.set_xlabel("Mois", fontsize=self.font_sizes["normal"])
        ax.set_ylabel("Montant (TND)", fontsize=self.font_sizes["normal"])
        ax.set_title("Évolution des revenus et dépenses (6 derniers mois)", 
                    fontsize=self.font_sizes["subtitle"], pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha='right', fontsize=self.font_sizes["normal"]-1)
        ax.legend(fontsize=self.font_sizes["normal"])
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        graph_canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        graph_canvas.draw()
        graph_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def create_responsive_table(self):
        """Crée le tableau des dernières dépenses responsive"""
        table_frame = tk.Frame(self.parent_frame, bg="white")
        table_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        ResponsiveManager.configure_grid(table_frame, [0, 1], [1])

        # Titre
        title_label = tk.Label(
            table_frame,
            text="🕒 Dernières dépenses",
            font=("Arial", self.font_sizes["subtitle"], "bold"),
            bg="white", fg="#2c3e50"
        )
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Tableau avec scroll
        table_container = tk.Frame(table_frame, bg="white")
        table_container.grid(row=1, column=0, sticky="nsew")
        ResponsiveManager.configure_grid(table_container, [1], [1, 0])

        columns = ("Date", "Montant", "Catégorie", "Description")
        tree = ttk.Treeview(table_container, columns=columns, show="headings", height=5)
        tree.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        # Configuration des colonnes
        for col in columns:
            tree.heading(col, text=col)
            if col == "Date":
                tree.column(col, width=80, minwidth=60)
            elif col == "Montant":
                tree.column(col, width=90, minwidth=70)
            elif col == "Catégorie":
                tree.column(col, width=100, minwidth=80)
            else:
                tree.column(col, width=150, minwidth=100)

        # Remplissage des données
        dernieres_depenses = get_dernieres_depenses(self.compte_actif, 5)
        for dep in dernieres_depenses:
            tree.insert("", "end", values=(dep[0], f"{dep[1]:.2f}", dep[2], dep[3] or "-"))

    # Les méthodes existantes restent inchangées
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
            start = datetime.datetime(year, month, 1)
            if month == 12:
                end = datetime.datetime(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end = datetime.datetime(year, month + 1, 1) - datetime.timedelta(days=1)
            month_name = start.strftime("%B %Y")
            revenus = get_revenus_pour_periode(self.compte_actif, start, end)
            depenses = get_total_depenses_pour_periode(self.compte_actif, start, end)
            result.append((month_name, revenus, depenses))
        return result[::-1]