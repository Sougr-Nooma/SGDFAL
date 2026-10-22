import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
import database
from database import get_depenses_par_categorie, ajouter_depense
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class Depenses:
    def __init__(self, parent_frame, compte_actif):
        self.parent_frame = parent_frame
        self.compte_actif = compte_actif
        # Définir les catégories par type
        self.categories_fixes = ["LOYER/TAXES", "INTERNET", "TPE"]
        self.categories_variables = [
            "CUISINE", "COMPTOIRE", "CHICHA", "SALAIRE",
            "ÉLECTRICITÉ", "EAU", "IMPOT", "AUTRE"]
        
        # Variables pour stocker les canvas des graphiques
        self.canvas_pie = None
        self.canvas_bar = None
        self.pie_frame = None
        self.bar_frame = None

    def afficher(self):
        """Affiche la page Dépenses avec défilement complet"""
        # Effacer tout contenu existant
        for widget in self.parent_frame.winfo_children():
            widget.destroy()

        # === Créer un Canvas + Frame scrollable ===
        scroll_canvas = tk.Canvas(self.parent_frame, bg="white")
        scrollbar = ttk.Scrollbar(self.parent_frame, orient="vertical", command=scroll_canvas.yview)
        
        # Frame principal centré
        main_frame = tk.Frame(scroll_canvas, bg="white")
        
        # Associer le frame au canvas
        main_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        scroll_canvas.create_window((scroll_canvas.winfo_width()//2, 0), window=main_frame, anchor="n")
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        # Gestion de la souris (défilement)
        def _on_mousewheel(event):
            scroll_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        main_frame.bind_all("<MouseWheel>", _on_mousewheel)
        main_frame.bind_all("<Button-4>", lambda e: scroll_canvas.yview_scroll(-1, "units"))
        main_frame.bind_all("<Button-5>", lambda e: scroll_canvas.yview_scroll(1, "units"))

        # Positionner Canvas et Scrollbar
        scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # === Conteneur centré pour tout le contenu ===
        content_container = tk.Frame(main_frame, bg="white")
        content_container.pack(expand=True, fill="both", padx=50)

        # === Titre à gauche et bouton à droite ===
        top_frame = tk.Frame(content_container, bg="white")
        top_frame.pack(fill="x", padx=20, pady=15)
        
        tk.Label(
            top_frame,
            text="💸 Gestion des Dépenses",
            font=("Arial", 18, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(side="left", padx=10)
        
        btn_ajouter = tk.Button(
            top_frame,
            text="➕ Ajouter une dépense",
            bg="#2ecc71",
            fg="white",
            font=("Arial", 12),
            command=self.ouvrir_formulaire_ajout
        )
        btn_ajouter.pack(side="right", padx=10)

        # === Filtre centré ===
        filter_frame = tk.Frame(content_container, bg="white")
        filter_frame.pack(pady=10, fill="x")
        
        tk.Label(filter_frame, text="Filtrer par :", bg="white", font=("Arial", 11)).pack(side="left", padx=(0, 10))
        
        self.filter_var = tk.StringVar(value="TOUT")
        combo_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["TOUT", "FIXES", "VARIABLES", "INTERMEDIAIRES", "INDIVIDUS"],
            state="readonly",
            font=("Arial", 11),
            width=15
        )
        combo_filter.pack(side="left")
        combo_filter.bind("<<ComboboxSelected>>", self.on_filter_changed)

        # Centrer le frame du filtre
        filter_frame.pack(anchor="center")

        # === Tableau des 7 dernières dépenses ===
        tk.Label(
            content_container,
            text="📋 Liste des dernières dépenses",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(pady=(20, 10), anchor="center")

        # Conteneur pour le tableau centré
        table_container = tk.Frame(content_container, bg="white")
        table_container.pack(fill="x", pady=10, padx=50)

        columns = ("Date", "Montant", "Catégorie", "Fournisseur", "Description")
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", height=7)
        
        # Configuration des colonnes centrées
        for col in columns:
            self.tree.heading(col, text=col, anchor="center")
            if col == "Date":
                self.tree.column(col, width=100, anchor="center")
            elif col == "Montant":
                self.tree.column(col, width=100, anchor="center")
            elif col == "Catégorie":
                self.tree.column(col, width=120, anchor="center")
            elif col == "Fournisseur":
                self.tree.column(col, width=140, anchor="center")
            else:
                self.tree.column(col, width=200, anchor="center")
        
        self.tree.pack(side="left", fill="x", expand=True)

        # Scrollbar du tableau
        tree_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")

        self.charger_depenses()

        
        # === SECTION DES GRAPHIQUES CÔTE À CÔTE ===
        tk.Label(
            content_container,
            text="📊 Statistiques des Dépenses",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(pady=(30, 20), anchor="center")

        graphs_container = tk.Frame(content_container, bg="white")
        graphs_container.pack(fill="both", expand=True, pady=10)

        # === Camembert ===
        self.pie_frame = tk.Frame(graphs_container, bg="white")
        self.pie_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.pie_label = tk.Label(self.pie_frame, text="Répartition en pourcentage", font=("Arial", 11, "bold"), bg="white")
        self.pie_label.pack(pady=(0, 10))

        # === Barres ===
        self.bar_frame = tk.Frame(graphs_container, bg="white")
        self.bar_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
        self.bar_label = tk.Label(self.bar_frame, text="Montant par catégorie", font=("Arial", 11, "bold"), bg="white")
        self.bar_label.pack(pady=(0, 10))

        # Charger les graphiques initiaux
        self.mettre_a_jour_graphiques()

        # Mise à jour du canvas pour centrer le contenu
        def update_canvas_width(event):
            scroll_canvas.itemconfig(scroll_canvas.find_all(), width=event.width)
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        
        scroll_canvas.bind("<Configure>", update_canvas_width)
        
    def on_filter_changed(self, event=None):
        """Appelé quand le filtre change - met à jour tableau ET graphiques"""
        self.charger_depenses()
        self.mettre_a_jour_graphiques()
        
    def mettre_a_jour_graphiques(self):
        """Met à jour les deux graphiques selon le filtre actuel"""
        # Détruire les anciens canvas s'ils existent
        if self.canvas_pie:
            self.canvas_pie.get_tk_widget().destroy()
        if self.canvas_bar:
            self.canvas_bar.get_tk_widget().destroy()
        
        filtre = self.filter_var.get()
        donnees = self.get_donnees_graphiques(filtre)
        
        # Mettre à jour les titres selon le filtre
        if filtre == "TOUT":
            self.pie_label.config(text="Répartition par type de dépenses")
            self.bar_label.config(text="Montant par type de dépenses")
        else:
            type_map = {
                "FIXES": "dépenses fixes",
                "VARIABLES": "dépenses variables",
                "INTERMEDIAIRES": "dépenses intermédiaires",
                "INDIVIDUS": "dépenses individus"
            }
            type_text = type_map.get(filtre, "catégories")
            self.pie_label.config(text=f"Répartition des {type_text}")
            self.bar_label.config(text=f"Montant des {type_text}")

        # === CAMEMBERT ===
        fig_pie, ax_pie = plt.subplots(figsize=(5.5, 4.5))
        if donnees:
            labels = [item[0] for item in donnees]
            valeurs = [item[1] for item in donnees]
            ax_pie.pie(valeurs, labels=labels, autopct='%1.1f%%', startangle=90)
            ax_pie.axis('equal')
        else:
            ax_pie.text(0.5, 0.5, "Aucune donnée", ha='center', va='center')
            ax_pie.axis('equal')
        fig_pie.tight_layout(pad=2.5)
        self.canvas_pie = FigureCanvasTkAgg(fig_pie, master=self.pie_frame)
        self.canvas_pie.draw()
        self.canvas_pie.get_tk_widget().pack(fill="both", expand=True)

        # === BARRES ===
        fig_bar, ax_bar = plt.subplots(figsize=(6.5, 5))
        if donnees:
            labels = [item[0] for item in donnees]
            valeurs = [item[1] for item in donnees]
            x = range(len(labels))
            ax_bar.bar(x, valeurs, color="#2ecc71", alpha=0.8)
            ax_bar.set_xticks(x)
            ax_bar.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
            ax_bar.set_ylabel("Montant (TND)", fontsize=10)
            fig_bar.subplots_adjust(left=0.12, right=0.95, bottom=0.32, top=0.95)
        else:
            ax_bar.text(0.5, 0.5, "Aucune donnée", ha='center', va='center')
        self.canvas_bar = FigureCanvasTkAgg(fig_bar, master=self.bar_frame)
        self.canvas_bar.draw()
        self.canvas_bar.get_tk_widget().pack(fill="both", expand=True, pady=(0, 20))
        
    def get_donnees_graphiques(self, filtre):
        """Renvoie les données pour les graphiques selon le filtre"""
        conn = database.connect_db()
        cursor = conn.cursor()
        
        if filtre == "TOUT":
            # Agrégation par type_depense
            cursor.execute("""
                SELECT type_depense, SUM(montant)
                FROM depenses
                WHERE compte = ? AND type_depense IS NOT NULL
                GROUP BY type_depense
                ORDER BY SUM(montant) DESC
            """, (self.compte_actif,))
            result = cursor.fetchall()
            # Renommer pour affichage
            mapping = {
                "FIXES": "Dépenses fixes",
                "VARIABLES": "Dépenses variables",
                "INTERMEDIAIRES": "Dépenses intermédiaires",
                "INDIVIDUS": "Dépenses individus"
            }
            result = [(mapping.get(r[0], r[0]), r[1]) for r in result if r[0]]
        else:
            # Agrégation par catégorie pour un type donné
            cursor.execute("""
                SELECT categorie, SUM(montant)
                FROM depenses
                WHERE compte = ? AND type_depense = ?
                GROUP BY categorie
                ORDER BY SUM(montant) DESC
            """, (self.compte_actif, filtre))
            result = cursor.fetchall()
        
        conn.close()
        return result

    def get_all_depenses_filtered(self, compte, filter_type):
        """Récupère les dépenses filtrées par type (TOUT / FIXES / VARIABLES)"""
        conn = database.connect_db()
        cursor = conn.cursor()
        if filter_type == "TOUT":
            query = """
                SELECT date, montant, categorie, fournisseur, description 
                FROM depenses 
                WHERE compte = ? 
                ORDER BY date DESC LIMIT 10
            """
            cursor.execute(query, (compte,))
        else:
            # Utiliser type_depense au lieu de catégorie
            query = """
                SELECT date, montant, categorie, fournisseur, description 
                FROM depenses 
                WHERE compte = ? AND type_depense = ?
                ORDER BY date DESC LIMIT 10
            """
            cursor.execute(query, (compte, filter_type))
        
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_depenses_fixes_par_categorie(self):
        """Renvoie les dépenses fixes (Loyer, Internet, TPE) par catégorie"""
        conn = database.connect_db()
        cursor = conn.cursor()
        categories = tuple(self.categories_fixes)
        placeholders = ','.join(['?'] * len(categories))
        query = f'''
            SELECT categorie, SUM(montant)
            FROM depenses 
            WHERE compte = ? AND categorie IN ({placeholders})
            GROUP BY categorie 
            ORDER BY SUM(montant) DESC
        '''
        cursor.execute(query, (self.compte_actif,) + categories)
        result = cursor.fetchall()
        conn.close()
        return result

    def get_depenses_variables_par_categorie(self):
        """Renvoie les dépenses variables (Cuisine, Comptoir, etc.) par catégorie"""
        conn = database.connect_db()
        cursor = conn.cursor()
        categories = tuple(self.categories_variables)
        placeholders = ','.join(['?'] * len(categories))
        query = f'''
            SELECT categorie, SUM(montant)
            FROM depenses 
            WHERE compte = ? AND categorie IN ({placeholders})
            GROUP BY categorie 
            ORDER BY SUM(montant) DESC
        '''
        cursor.execute(query, (self.compte_actif,) + categories)
        result = cursor.fetchall()
        conn.close()
        return result
    
    
    def charger_depenses(self, event=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        filter_type = self.filter_var.get()

        depenses = self.get_all_depenses_filtered(self.compte_actif, filter_type)
        for dep in depenses:
            sql_date = dep[0]  # Ex: "2025-09-18"
            # Conversion : YYYY-MM-DD → DD/MM/YYYY
            try:
                date_obj = datetime.strptime(sql_date, "%Y-%m-%d")
                display_date = date_obj.strftime("%d/%m/%Y")
            except Exception:
                display_date = "Date invalide"
                
            self.tree.insert("", "end", values=(
                display_date,
                f"{dep[1]:.2f} TND",
                dep[2],
                dep[3] or "-",
                dep[4] or "-"
            ))

    def ouvrir_formulaire_ajout(self):
        ajout_fenetre = tk.Toplevel(self.parent_frame)
        ajout_fenetre.title("Ajouter une dépense")
        ajout_fenetre.geometry("400x650")
        ajout_fenetre.resizable(False, False)
        ajout_fenetre.transient(self.parent_frame)
        ajout_fenetre.grab_set()
        ajout_fenetre.configure(bg="#f0f0f0")
        frame_central = tk.Frame(ajout_fenetre, bg="#f0f0f0")
        frame_central.pack(expand=True, padx=20, pady=20)

        # --- Date ---
        tk.Label(frame_central, text="Date :", bg="#f0f0f0").pack(pady=5)
        btn_date = tk.Button(
            frame_central,
            text=datetime.now().strftime("%d/%m/%Y"),
            command=lambda: self.ouvrir_calendrier(btn_date),
            bg="white",
            fg="black",
            font=("Arial", 10),
            relief="solid"
        )
        btn_date.pack(pady=5, padx=20, fill="x")

        # --- Montant ---
        tk.Label(frame_central, text="Montant (TND) :", bg="#f0f0f0").pack(pady=5)
        montant_var = tk.DoubleVar(value=0.0)
        spinbox_montant = tk.Spinbox(
            frame_central,
            textvariable=montant_var,
            from_=0.01,
            to=99999.99,
            increment=0.01,
            font=("Arial", 12),
            justify="right"
        )
        spinbox_montant.pack(pady=5, padx=20, fill="x")

        # --- Type de dépenses ---
        tk.Label(frame_central, text="Type de dépenses :", bg="#f0f0f0").pack(pady=5)
        type_depense_var = tk.StringVar(value="Dépenses variables")
        combo_type = ttk.Combobox(
            frame_central,
            textvariable=type_depense_var,
            values=["Dépenses fixes", "Dépenses variables", "Dépenses intermédiaires", "Dépenses individus"],
            state="readonly",
            font=("Arial", 12)
        )
        combo_type.pack(pady=5, padx=20, fill="x")

        # --- Label "Catégorie" (toujours visible) ---
        tk.Label(frame_central, text="Catégorie :", bg="#f0f0f0").pack(pady=5)

        # Conteneur pour alterner entre combo et champ de saisie
        cat_container = tk.Frame(frame_central, bg="#f0f0f0")
        cat_container.pack(pady=5, padx=20, fill="x")

        # Combobox pour catégories fixes/variables
        combo_categorie = ttk.Combobox(
            cat_container,
            state="readonly",
            font=("Arial", 12)
        )

        # Champ de saisie pour intermédiaires/individus
        entry_categorie = tk.Entry(cat_container, font=("Arial", 12))
        entry_categorie.insert(0, "Nom de la dépense")
        entry_categorie.config(fg="grey")
        entry_categorie.bind("<FocusIn>", lambda e: entry_categorie.delete(0, "end") if entry_categorie.get() == "Nom de la dépense" else None)
        entry_categorie.bind("<FocusOut>", lambda e: entry_categorie.insert(0, "Nom de la dépense") if not entry_categorie.get() else None)

        def mettre_a_jour_interface(event=None):
            t = type_depense_var.get()
            combo_categorie.pack_forget()
            entry_categorie.pack_forget()
            if t in ["Dépenses fixes", "Dépenses variables"]:
                combo_categorie.pack(fill="x")
                if t == "Dépenses fixes":
                    combo_categorie['values'] = self.categories_fixes
                    combo_categorie.set(self.categories_fixes[0] if self.categories_fixes else "")
                else:
                    combo_categorie['values'] = self.categories_variables
                    combo_categorie.set(self.categories_variables[0] if self.categories_variables else "")
            else:
                entry_categorie.pack(fill="x")

        combo_type.bind("<<ComboboxSelected>>", mettre_a_jour_interface)
        mettre_a_jour_interface()  # Initialisation

        # --- Fournisseur ---
        tk.Label(frame_central, text="Fournisseur (optionnel) :", bg="#f0f0f0").pack(pady=5)
        entry_fournisseur = tk.Entry(frame_central, font=("Arial", 12))
        entry_fournisseur.insert(0, "Ex: Marché Central")
        entry_fournisseur.config(fg="grey")
        entry_fournisseur.bind("<FocusIn>", lambda e: entry_fournisseur.delete(0, "end") if entry_fournisseur.get() == "Ex: Marché Central" else None)
        entry_fournisseur.bind("<FocusOut>", lambda e: entry_fournisseur.insert(0, "Ex: Marché Central") if not entry_fournisseur.get() else None)
        entry_fournisseur.pack(pady=5, padx=20, fill="x")

        # --- Description ---
        tk.Label(frame_central, text="Description (optionnel) :", bg="#f0f0f0").pack(pady=5)
        text_description = tk.Text(frame_central, font=("Arial", 12), height=3, relief="solid", bd=1)
        text_description.pack(pady=5, padx=20, fill="x")

        # === Validation et ajout ===
        def ajouter():
            # Date
            date_str = btn_date.cget("text")
            if date_str == "Cliquez pour choisir la date":
                messagebox.showwarning("Erreur", "Veuillez sélectionner une date.")
                return
            try:
                day, month, year = map(int, date_str.split('/'))
                if len(str(year)) != 4:
                    raise ValueError
            except:
                messagebox.showwarning("Erreur", "Format de date invalide. Utilisez jj/mm/aaaa.")
                return

            montant = montant_var.get()
            if montant <= 0:
                messagebox.showwarning("Erreur", "Le montant doit être supérieur à 0.")
                return

            # Récupérer le type
            type_selectionne = type_depense_var.get()
            if type_selectionne == "Dépenses fixes":
                type_db = "FIXES"
                categorie = combo_categorie.get()
            elif type_selectionne == "Dépenses variables":
                type_db = "VARIABLES"
                categorie = combo_categorie.get()
            elif type_selectionne == "Dépenses intermédiaires":
                type_db = "INTERMEDIAIRES"
                categorie = entry_categorie.get().strip()
            else:  # Dépenses individus
                type_db = "INDIVIDUS"
                categorie = entry_categorie.get().strip()

            # Validation
            if not categorie or (type_selectionne in ["Dépenses intermédiaires", "Dépenses individus"] and categorie == "Nom de la dépense"):
                messagebox.showwarning("Erreur", "Veuillez entrer un nom de dépense valide.")
                return

            fournisseur = entry_fournisseur.get().strip()
            if fournisseur == "Ex: Marché Central":
                fournisseur = ""
            description = text_description.get("1.0", "end-1c").strip()

            sql_date = f"{year}-{month:02d}-{day:02d}"
            if ajouter_depense(sql_date, montant, categorie, fournisseur, description, self.compte_actif, type_db):
                messagebox.showinfo("Succès", "Dépense ajoutée avec succès.")
                self.charger_depenses()
                self.mettre_a_jour_graphiques()  # Mettre à jour les graphiques
                ajout_fenetre.destroy()
            else:
                messagebox.showerror("Erreur", "Échec de l'ajout.")

        # Boutons
        tk.Button(frame_central, text="✅ Valider la dépense", bg="#2ecc71", fg="white", command=ajouter).pack(pady=15, padx=20, fill="x")
        tk.Button(frame_central, text="❌ Annuler", bg="#e74c3c", fg="white", command=ajout_fenetre.destroy).pack(pady=5, padx=20, fill="x")
        

    def ouvrir_calendrier(self, btn_date):
        """Ouvre le calendrier et met à jour le bouton avec la date choisie"""
        cal_window = tk.Toplevel(self.parent_frame.winfo_toplevel())
        cal_window.title("Choisir la date")
        cal_window.geometry("400x500")
        cal_window.configure(bg="white")
        cal_window.transient(self.parent_frame.winfo_toplevel())
        cal_window.grab_set()
        cal_window.focus_force()

        # Créer le calendrier
        cal = Calendar(
            cal_window,
            selectmode='day',
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day,
            background="white",
            foreground="black",
            headerbackground="lightgray",
            headerforeground="black",
            weekendbackground="#f0f0f0",
            weekendforeground="darkgreen",
            normalbackground="white",
            normalforeground="black",
            font=('Arial', 10),
            relief='flat'
        )
        cal.pack(padx=10, pady=10, fill="both", expand=True)

        # Forcer la sélection initiale
        cal.selection_set(datetime.now().date())

        def on_date_selected(event):
            selected_date_str = cal.get_date()
            try:
                parsed_date = datetime.strptime(selected_date_str, "%m/%d/%y")
                day = parsed_date.day
                month = parsed_date.month
                year = parsed_date.year
                
                # Convertir 25 → 2025, etc.
                if year < 2000:
                    year += 2000
                    
                formatted_date = f"{day:02d}/{month:02d}/{year}"
                btn_date.config(text=formatted_date)
                cal_window.destroy()

            except ValueError as e:
                print("Erreur lors de la lecture de la date:", e)
                messagebox.showerror("Erreur", "Format de date invalide.")
        cal.bind("<<CalendarSelected>>", on_date_selected)

        # Attendre la fermeture de la fenêtre
        cal_window.wait_window()