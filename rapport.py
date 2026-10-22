import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import Calendar
from datetime import datetime, timedelta
import database
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from database import get_all_depenses_by_compte, get_all_revenus_by_compte, get_categories_for_type
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

class Rapport:
    @staticmethod
    def ajuster_largeur_colonnes_excel(ws, largeur_min=10, largeur_max=50):
        """Adapte la largeur des colonnes au contenu visible de la feuille."""
        plages_fusionnees = tuple(ws.merged_cells.ranges)
        largeurs = {}

        for ligne in ws.iter_rows():
            for cellule in ligne:
                if cellule.value is None:
                    continue
                if any(
                    plage.min_row <= cellule.row <= plage.max_row
                    and plage.min_col <= cellule.column <= plage.max_col
                    for plage in plages_fusionnees
                ):
                    continue

                longueur = len(str(cellule.value))
                largeurs[cellule.column] = max(largeurs.get(cellule.column, 0), longueur)

        for colonne, longueur in largeurs.items():
            lettre = get_column_letter(colonne)
            ws.column_dimensions[lettre].width = max(
                largeur_min, min(longueur + 2, largeur_max)
            )

    def __init__(self, parent_frame, compte_actif):
        self.parent_frame = parent_frame
        self.compte_actif = compte_actif
        self.type_finances = "Dépenses"
        self.periode_selectionnee = "Mois"
        self.date_selectionnee = datetime.now().date()

    def afficher(self):
        """Affiche l'interface de génération de rapport"""
        for widget in self.parent_frame.winfo_children():
            widget.destroy()

        # === Titre principal ===
        title_label = tk.Label(
            self.parent_frame,
            text="📊 Générateur de Rapports",
            font=("Arial", 18, "bold"),
            bg="white",
            fg="#2c3e50",
            anchor="center"
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(20, 10), sticky="ew")

        # === Cadre de configuration ===
        config_frame = tk.Frame(self.parent_frame, bg="#f9f9f9", bd=1, relief="solid")
        config_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        config_frame.columnconfigure(1, weight=1)

        # --- Type de finances ---
        tk.Label(config_frame, text="Type de finances :", font=("Arial", 10, "bold"), bg="#f9f9f9").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.type_var = tk.StringVar(value="TOUT")
        combo_type = ttk.Combobox(
            config_frame,
            textvariable=self.type_var,
            values=["TOUT", "Dépenses", "Revenus"],
            state="readonly",
            font=("Arial", 10)
        )
        combo_type.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        combo_type.bind("<<ComboboxSelected>>", self.mettre_a_jour_type_depenses)

        # --- Type de dépenses (nouveau champ) ---
        self.label_type_depense = tk.Label(config_frame, text="Type de dépenses :", font=("Arial", 10, "bold"), bg="#f9f9f9")
        self.label_type_depense.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.type_depense_var = tk.StringVar(value="TOUT")
        self.combo_type_depense = ttk.Combobox(
            config_frame,
            textvariable=self.type_depense_var,
            values=["TOUT", "FIXES", "VARIABLES", "INTERMEDIAIRES", "INDIVIDUS"],
            state="readonly",
            font=("Arial", 10)
        )
        self.combo_type_depense.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.combo_type_depense.bind("<<ComboboxSelected>>", self.mettre_a_jour_categories)

        # --- Catégorie ---
        tk.Label(config_frame, text="Catégorie :", font=("Arial", 10, "bold"), bg="#f9f9f9").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.categorie_var = tk.StringVar(value="")
        self.combo_categorie = ttk.Combobox(
            config_frame,
            textvariable=self.categorie_var,
            state="readonly",
            font=("Arial", 10)
        )
        self.combo_categorie.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # --- Période ---
        tk.Label(config_frame, text="Période :", font=("Arial", 10, "bold"), bg="#f9f9f9").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.periode_var = tk.StringVar(value="Mois")
        combo_periode = ttk.Combobox(
            config_frame,
            textvariable=self.periode_var,
            values=["Jour", "Semaine", "Mois", "Année"],
            state="readonly",
            font=("Arial", 10)
        )
        combo_periode.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        combo_periode.bind("<<ComboboxSelected>>", self.changer_periode)

        # --- Date de référence ---
        tk.Label(config_frame, text="Date de référence :", font=("Arial", 10, "bold"), bg="#f9f9f9").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.btn_date = tk.Button(
            config_frame,
            text=self.format_date_affichage(),
            command=self.ouvrir_calendrier,
            bg="white",
            fg="black",
            font=("Arial", 10),
            padx=10,
            pady=5,
            width=15,
            borderwidth=1,
            relief="solid",
            highlightbackground="#ccc"
        )
        self.btn_date.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        # Initialiser l'affichage
        self.mettre_a_jour_type_depenses()

        # === Bouton Générer ===
        btn_generer = tk.Button(
            self.parent_frame,
            text="✅ Générer le rapport",
            bg="#3498db",
            fg="white",
            font=("Arial", 12, "bold"),
            command=self.generer_rapport,
            activebackground="#2980b9",
            activeforeground="white",
            padx=20,
            pady=10,
            relief="raised",
            bd=2
        )
        btn_generer.grid(row=2, column=0, columnspan=2, pady=20, sticky="ew")

        # === Zone d'affichage du rapport ===
        self.resultat_text = tk.Text(
            self.parent_frame,
            height=12,
            font=("Consolas", 10),
            wrap="word",
            bg="#f9f9f9",
            fg="#2c3e50",
            state="disabled",
            relief="solid",
            bd=1
        )
        self.resultat_text.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        # === Boutons export ===
        export_frame = tk.Frame(self.parent_frame, bg="white")
        export_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")

        btn_export_excel = tk.Button(
            export_frame,
            text="📥 Exporter en Excel",
            bg="#2ecc71",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.exporter_excel,
            activebackground="#27ae60",
            activeforeground="white",
            padx=15,
            pady=5,
            relief="raised",
            bd=2
        )
        btn_export_excel.pack(side="left", padx=(20, 10))

        btn_export_pdf = tk.Button(
            export_frame,
            text="📄 Exporter en PDF",
            bg="#e74c3c",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.exporter_pdf,
            activebackground="#c0392b",
            activeforeground="white",
            padx=15,
            pady=5,
            relief="raised",
            bd=2
        )
        btn_export_pdf.pack(side="right", padx=(10, 20))

        # Configurer la grille
        self.parent_frame.columnconfigure(0, weight=1)
        self.parent_frame.rowconfigure(3, weight=1)

    def mettre_a_jour_type_depenses(self, event=None):
        """Affiche/masque le champ 'Type de dépenses' selon le type de finances"""
        type_val = self.type_var.get()
        
        if type_val == "Dépenses":
            # Afficher le champ type de dépenses et catégorie
            self.label_type_depense.grid()
            self.combo_type_depense.grid()
        elif type_val == "TOUT":
            # Masquer type de dépenses et catégorie pour TOUT
            self.label_type_depense.grid_remove()
            self.combo_type_depense.grid_remove()
        else:
            # Masquer le champ type de dépenses pour les revenus
            self.label_type_depense.grid_remove()
            self.combo_type_depense.grid_remove()
        
        # Mettre à jour les catégories
        self.mettre_a_jour_categories()

    def mettre_a_jour_categories(self, event=None):
        """Met à jour la liste des catégories selon le type sélectionné"""
        type_val = self.type_var.get()
        
        if type_val == "TOUT":
            # Afficher la combobox catégorie avec les options
            self.combo_categorie.grid()
            try:
                self.combo_categorie.master.children['!label3'].grid()
            except:
                pass
            
            self.combo_categorie['values'] = ["REVENUS ET DÉPENSES", "2 à 2"]
            self.categorie_var.set("REVENUS ET DÉPENSES")
            
            # Vérifier si "2 à 2" pour afficher les filtres supplémentaires
            self.combo_categorie.bind("<<ComboboxSelected>>", self.gerer_option_2a2)
        elif type_val == "Dépenses":
            # Afficher la combobox catégorie
            self.combo_categorie.grid()
            try:
                self.combo_categorie.master.children['!label3'].grid()
            except:
                pass
            
            type_depense = self.type_depense_var.get()
            categories = self.get_categories_depenses(type_depense)
            
            # Ajouter l'option "Toutes"
            if type_depense == "TOUT":
                all_option = "Tout(e)s les Dépenses"
            else:
                all_option = f"Toutes les dépenses {type_depense.lower()}"
            
            categories = [all_option] + categories
            self.combo_categorie['values'] = categories
            if categories:
                self.categorie_var.set(categories[0])
        else:
            # Pour les revenus
            self.combo_categorie.grid()
            try:
                self.combo_categorie.master.children['!label3'].grid()
            except:
                pass
            
            categories = get_categories_for_type("Revenus", self.compte_actif)
            all_option = "Tout(e)s les Revenus"
            categories = [all_option] + categories
            self.combo_categorie['values'] = categories
            if categories:
                self.categorie_var.set(categories[0])
            else:
                self.categorie_var.set("")

    def gerer_option_2a2(self, event=None):
        """Gère l'affichage des filtres supplémentaires pour l'option '2 à 2'"""
        if self.categorie_var.get() == "2 à 2":
            self.afficher_filtres_2a2()
        else:
            self.masquer_filtres_2a2()

    def afficher_filtres_2a2(self):
        """Affiche les deux menus déroulants pour l'option '2 à 2'"""
        # Créer le cadre s'il n'existe pas
        if not hasattr(self, 'frame_2a2'):
            config_frame = self.combo_categorie.master
            
            self.frame_2a2 = tk.Frame(config_frame, bg="#f9f9f9", bd=1, relief="solid")
            self.frame_2a2.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
            
            # Titre du cadre
            tk.Label(
                self.frame_2a2, 
                text="Configuration 2 à 2", 
                font=("Arial", 10, "bold"), 
                bg="#f9f9f9"
            ).grid(row=0, column=0, columnspan=2, pady=(5, 10))
            
            # Menu 1 : Dépenses Falaise
            tk.Label(
                self.frame_2a2, 
                text="Dépenses Falaise :", 
                font=("Arial", 9), 
                bg="#f9f9f9"
            ).grid(row=1, column=0, padx=10, pady=5, sticky="w")
            
            self.depenses_falaise_var = tk.StringVar(value="TOUT")
            self.combo_depenses_falaise = ttk.Combobox(
                self.frame_2a2,
                textvariable=self.depenses_falaise_var,
                values=["TOUT", "FIXES", "VARIABLES", "INTERMEDIAIRES"],
                state="readonly",
                font=("Arial", 9),
                width=20
            )
            self.combo_depenses_falaise.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
            
            # Menu 2 : Dépenses Individus
            tk.Label(
                self.frame_2a2, 
                text="Dépenses Individus :", 
                font=("Arial", 9), 
                bg="#f9f9f9"
            ).grid(row=2, column=0, padx=10, pady=5, sticky="w")
            
            # Récupérer les catégories des dépenses INDIVIDUS
            categories_individus = self.get_categories_depenses("INDIVIDUS")
            valeurs_individus = ["TOUT"] + categories_individus
            
            self.depenses_individus_var = tk.StringVar(value="TOUT")
            self.combo_depenses_individus = ttk.Combobox(
                self.frame_2a2,
                textvariable=self.depenses_individus_var,
                values=valeurs_individus,
                state="readonly",
                font=("Arial", 9),
                width=20
            )
            self.combo_depenses_individus.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
            
            self.frame_2a2.columnconfigure(1, weight=1)
        else:
            self.frame_2a2.grid()

    def masquer_filtres_2a2(self):
        """Masque les filtres '2 à 2'"""
        if hasattr(self, 'frame_2a2'):
            self.frame_2a2.grid_remove()
    
    def get_categories_depenses(self, type_depense):
        """Récupère les catégories de dépenses selon le type"""
        conn = database.connect_db()
        cursor = conn.cursor()
        
        if type_depense == "TOUT":
            # Toutes les catégories
            cursor.execute("""
                SELECT DISTINCT categorie 
                FROM depenses 
                WHERE compte = ? AND categorie IS NOT NULL 
                ORDER BY categorie
            """, (self.compte_actif,))
        else:
            # Catégories d'un type spécifique
            cursor.execute("""
                SELECT DISTINCT categorie 
                FROM depenses 
                WHERE compte = ? AND type_depense = ? AND categorie IS NOT NULL 
                ORDER BY categorie
            """, (self.compte_actif, type_depense))
        
        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result

    def changer_periode(self, event=None):
        """Mise à jour de la date affichée selon la période choisie"""
        self.periode_selectionnee = self.periode_var.get()
        self.date_selectionnee = self.calculer_date_reference()
        self.btn_date.config(text=self.format_date_affichage())

    def calculer_date_reference(self):
        """Calcule la date de référence selon la période choisie"""
        today = datetime.now().date()
        if self.periode_selectionnee == "Jour":
            return today
        elif self.periode_selectionnee == "Semaine":
            start_of_week = today - timedelta(days=today.weekday())
            return start_of_week
        elif self.periode_selectionnee == "Mois":
            return today.replace(day=1)
        elif self.periode_selectionnee == "Année":
            return today.replace(month=1, day=1)
        return today

    def format_date_affichage(self):
        """Formate la date pour l'affichage sur le bouton"""
        if not isinstance(self.date_selectionnee, datetime):
            self.date_selectionnee = datetime.combine(self.date_selectionnee, datetime.min.time())
        if self.periode_selectionnee == "Jour":
            return self.date_selectionnee.strftime("%d/%m/%Y")
        elif self.periode_selectionnee == "Semaine":
            return f"Semaine du {self.date_selectionnee.strftime('%d/%m/%Y')}"
        elif self.periode_selectionnee == "Mois":
            return self.date_selectionnee.strftime("%B %Y").capitalize()
        elif self.periode_selectionnee == "Année":
            return str(self.date_selectionnee.year)
        return ""

    def ouvrir_calendrier(self):
        """Ouvre le calendrier pour sélectionner une date"""
        cal_window = tk.Toplevel(self.parent_frame.winfo_toplevel())
        cal_window.title(f"Sélectionner une date ({self.periode_selectionnee})")
        cal_window.geometry("400x500")
        cal_window.configure(bg="white")
        cal_window.transient(self.parent_frame.winfo_toplevel())
        cal_window.grab_set()
        cal_window.focus_force()

        cal = Calendar(
            cal_window,
            selectmode='day',
            year=self.date_selectionnee.year,
            month=self.date_selectionnee.month,
            day=self.date_selectionnee.day,
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

        def on_date_selected(event):
            selected_date = cal.get_date()
            month, day, year = map(int, selected_date.split('/'))
            if year < 100:
                if year <= 29:
                    year += 2000
                else:
                    year += 1900
            self.date_selectionnee = datetime(year, month, day).date()
            self.btn_date.config(text=self.format_date_affichage())
            cal_window.destroy()

        cal.bind("<<CalendarSelected>>", on_date_selected)

    def generer_rapport(self):
        """Génère le rapport et l'affiche dans le texte"""
        type_val = self.type_var.get()
        categorie = self.categorie_var.get()
        periode = self.periode_selectionnee
        date_ref = self.date_selectionnee

        if type_val == "TOUT":
            # Vérifier si c'est l'option "2 à 2"
            if categorie == "2 à 2":
                self.generer_rapport_2a2(periode, date_ref)
            else:
                self.generer_rapport_complet(periode, date_ref)

        self.resultat_text.config(state="normal")
        self.resultat_text.delete("1.0", tk.END)
        
        if type_val == "TOUT":
            # Générer les deux rapports
            self.generer_rapport_complet(periode, date_ref)
        elif type_val == "Dépenses":
            type_depense = self.type_depense_var.get()
            donnees = self.get_depenses_filtrees(categorie, date_ref, periode, type_depense)
            self.afficher_rapport_depenses(donnees, categorie, periode, date_ref)
        else:
            donnees = self.get_revenus_filtres(categorie, date_ref, periode)
            self.afficher_rapport_revenus(donnees, categorie, periode, date_ref)
                
        self.resultat_text.config(state="disabled")
    
    def generer_rapport_complet(self, periode, date_ref):
        """Génère le rapport complet (Dépenses + Revenus) côte à côte"""
        periode_affichage = self.formater_periode(periode, date_ref)
        
        titre = f"Rapport Complet {periode_affichage}"
        self.resultat_text.insert(tk.END, titre + "\n")
        self.resultat_text.insert(tk.END, "=" * 180 + "\n\n")
        
        # Récupérer les données
        donnees_depenses = self.get_depenses_filtrees("Tout(e)s les Dépenses", date_ref, periode, "TOUT")
        donnees_revenus = self.get_revenus_filtres("Tout(e)s les Revenus", date_ref, periode)
        
        # Regrouper les dépenses
        depenses_groupees = {}
        for donnee in donnees_depenses:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in depenses_groupees:
                depenses_groupees[cle] = 0
            depenses_groupees[cle] += montant
        
        # Organiser les dépenses
        dep_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(depenses_groupees.items()):
            if type_dep not in dep_organisees:
                dep_organisees[type_dep] = {}
            if source not in dep_organisees[type_dep]:
                dep_organisees[type_dep][source] = []
            dep_organisees[type_dep][source].append((categorie_item, montant_total))
        
        # Regrouper les revenus
        revenus_groupes = {}
        for donnee in donnees_revenus:
            date_str, montant, source, categorie_item = donnee
            cle = (categorie_item, source)
            if cle not in revenus_groupes:
                revenus_groupes[cle] = 0
            revenus_groupes[cle] += montant
        
        # Organiser les revenus
        rev_organisees = {}
        for (categorie_item, source), montant_total in sorted(revenus_groupes.items()):
            if categorie_item not in rev_organisees:
                rev_organisees[categorie_item] = []
            rev_organisees[categorie_item].append((source, montant_total))
        
        # Préparer les lignes pour affichage côte à côte
        lignes_dep = []
        lignes_rev = []
        
        # Construire les lignes de dépenses
        total_depenses = 0
        for type_dep in sorted(dep_organisees.keys()):
            type_printed = False
            for source in sorted(dep_organisees[type_dep].keys()):
                source_printed = False
                categories = dep_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    type_str = type_dep if not type_printed else ""
                    source_str = source if not source_printed else ""
                    
                    lignes_dep.append(f"{type_str:<15} {categorie_item:<20} {source_str:<15} {montant_total:>10.2f}")
                    total_depenses += montant_total
                    
                    if not type_printed:
                        type_printed = True
                    if not source_printed:
                        source_printed = True
        
        # Construire les lignes de revenus
        total_revenus = 0
        for categorie_item in sorted(rev_organisees.keys()):
            cat_printed = False
            for source, montant_total in rev_organisees[categorie_item]:
                cat_str = categorie_item if not cat_printed else ""
                
                lignes_rev.append(f"{cat_str:<25} {source:<25} {montant_total:>10.2f}")
                total_revenus += montant_total
                
                if not cat_printed:
                    cat_printed = True
        
        # Afficher les en-têtes côte à côte
        header_dep = f"{'📤 DÉPENSES':<70}"
        header_rev = f"{'📥 REVENUS':<70}"
        self.resultat_text.insert(tk.END, f"{header_dep}  |  {header_rev}\n")
        
        sub_header_dep = f"{'Type':<15} {'Catégorie':<20} {'Fournisseur':<15} {'Montant':>10}"
        sub_header_rev = f"{'Catégorie':<25} {'Source':<25} {'Montant':>10}"
        self.resultat_text.insert(tk.END, f"{sub_header_dep}  |  {sub_header_rev}\n")
        self.resultat_text.insert(tk.END, "-" * 70 + "  |  " + "-" * 70 + "\n")
        
        # Afficher les données côte à côte
        max_lignes = max(len(lignes_dep), len(lignes_rev))
        for i in range(max_lignes):
            ligne_dep = lignes_dep[i] if i < len(lignes_dep) else " " * 70
            ligne_rev = lignes_rev[i] if i < len(lignes_rev) else " " * 70
            self.resultat_text.insert(tk.END, f"{ligne_dep:<70}  |  {ligne_rev:<70}\n")
        
        # Totaux
        self.resultat_text.insert(tk.END, "-" * 70 + "  |  " + "-" * 70 + "\n")
        total_dep_str = f"{'TOTAL DÉPENSES:':<55} {total_depenses:>10.2f} TND"
        total_rev_str = f"{'TOTAL REVENUS:':<50} {total_revenus:>10.2f} TND"
        self.resultat_text.insert(tk.END, f"{total_dep_str:<70}  |  {total_rev_str:<70}\n")
        
        # === BILAN ===
        self.resultat_text.insert(tk.END, "\n" + "=" * 180 + "\n")
        self.resultat_text.insert(tk.END, "💰 BILAN FINANCIER\n")
        self.resultat_text.insert(tk.END, "=" * 180 + "\n")
        
        benefice = total_revenus - total_depenses
        self.resultat_text.insert(tk.END, f"{'Total Revenus:':<50} {total_revenus:>20.2f} TND\n")
        self.resultat_text.insert(tk.END, f"{'Total Dépenses:':<50} {total_depenses:>20.2f} TND\n")
        self.resultat_text.insert(tk.END, "-" * 180 + "\n")
        
        if benefice >= 0:
            self.resultat_text.insert(tk.END, f"{'✅ BÉNÉFICE:':<50} {benefice:>20.2f} TND\n")
        else:
            self.resultat_text.insert(tk.END, f"{'❌ PERTE:':<50} {abs(benefice):>20.2f} TND\n")
    
    def generer_rapport_2a2(self, periode, date_ref):
        """Génère le rapport comparatif 2 à 2 (Dépenses Falaise vs Dépenses Individus)"""
        periode_affichage = self.formater_periode(periode, date_ref)
        
        titre = f"Rapport Comparatif 2 à 2 - {periode_affichage}"
        self.resultat_text.insert(tk.END, titre + "\n")
        self.resultat_text.insert(tk.END, "=" * 180 + "\n\n")
        
        # Récupérer les filtres
        filtre_falaise = self.depenses_falaise_var.get()
        filtre_individus = self.depenses_individus_var.get()
        
        # Récupérer les dépenses Falaise
        if filtre_falaise == "TOUT":
            # Toutes les dépenses FIXES + VARIABLES + INTERMEDIAIRES
            donnees_falaise = []
            for type_dep in ["FIXES", "VARIABLES", "INTERMEDIAIRES"]:
                donnees_falaise.extend(
                    self.get_depenses_filtrees("Tout(e)s les Dépenses", date_ref, periode, type_dep)
                )
        else:
            donnees_falaise = self.get_depenses_filtrees(
                "Tout(e)s les Dépenses", date_ref, periode, filtre_falaise
            )
        
        # Récupérer les dépenses Individus
        if filtre_individus == "TOUT":
            donnees_individus = self.get_depenses_filtrees(
                "Tout(e)s les Dépenses", date_ref, periode, "INDIVIDUS"
            )
        else:
            # Filtrer par catégorie spécifique
            donnees_individus = [
                d for d in self.get_depenses_filtrees(
                    "Tout(e)s les Dépenses", date_ref, periode, "INDIVIDUS"
                )
                if d[3] == filtre_individus  # d[3] = categorie
            ]
        
        # Récupérer les revenus
        donnees_revenus = self.get_revenus_filtres("Tout(e)s les Revenus", date_ref, periode)
        
        # Traiter les dépenses Falaise
        depenses_falaise_groupees = {}
        for donnee in donnees_falaise:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in depenses_falaise_groupees:
                depenses_falaise_groupees[cle] = 0
            depenses_falaise_groupees[cle] += montant
        
        falaise_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(depenses_falaise_groupees.items()):
            if type_dep not in falaise_organisees:
                falaise_organisees[type_dep] = {}
            if source not in falaise_organisees[type_dep]:
                falaise_organisees[type_dep][source] = []
            falaise_organisees[type_dep][source].append((categorie_item, montant_total))
        
        # Traiter les dépenses Individus
        depenses_individus_groupees = {}
        for donnee in donnees_individus:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (categorie_item, source)
            if cle not in depenses_individus_groupees:
                depenses_individus_groupees[cle] = 0
            depenses_individus_groupees[cle] += montant
        
        individus_organisees = {}
        for (categorie_item, source), montant_total in sorted(depenses_individus_groupees.items()):
            if categorie_item not in individus_organisees:
                individus_organisees[categorie_item] = []
            individus_organisees[categorie_item].append((source, montant_total))
        
        # Traiter les revenus (format horizontal)
        revenus_par_date = {}
        for donnee in donnees_revenus:
            date_str, montant, source, categorie_item = donnee
            try:
                jour, mois, annee = date_str.split('/')
                date_key = f"{jour}/{mois}"
                date_obj = datetime(int(annee), int(mois), int(jour))
            except:
                date_key = date_str
                date_obj = datetime.now()
            
            if date_key not in revenus_par_date:
                revenus_par_date[date_key] = {'montant': 0, 'date_obj': date_obj}
            revenus_par_date[date_key]['montant'] += montant
        
        revenus_tries = sorted(revenus_par_date.items(), key=lambda x: x[1]['date_obj'])
        
        # Construire les lignes pour affichage
        lignes_falaise = []
        lignes_individus = []
        
        # Dépenses Falaise
        total_falaise = 0
        for type_dep in sorted(falaise_organisees.keys()):
            type_printed = False
            for source in sorted(falaise_organisees[type_dep].keys()):
                source_printed = False
                categories = falaise_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    type_str = type_dep if not type_printed else ""
                    source_str = source if not source_printed else ""
                    
                    lignes_falaise.append(f"{type_str:<15} {categorie_item:<20} {source_str:<15} {montant_total:>10.2f}")
                    total_falaise += montant_total
                    
                    if not type_printed:
                        type_printed = True
                    if not source_printed:
                        source_printed = True
        
        # Dépenses Individus
        total_individus = 0
        for categorie_item in sorted(individus_organisees.keys()):
            cat_printed = False
            for source, montant_total in individus_organisees[categorie_item]:
                cat_str = categorie_item if not cat_printed else ""
                
                lignes_individus.append(f"{cat_str:<25} {source:<20} {montant_total:>10.2f}")
                total_individus += montant_total
                
                if not cat_printed:
                    cat_printed = True
        
        # Afficher en colonnes
        header_falaise = f"{'📤 DÉPENSES FALAISE (' + filtre_falaise + ')':<70}"
        header_individus = f"{'👤 DÉPENSES INDIVIDUS (' + filtre_individus + ')':<70}"
        self.resultat_text.insert(tk.END, f"{header_falaise}  |  {header_individus}\n")
        
        sub_header_falaise = f"{'Type':<15} {'Catégorie':<20} {'Fournisseur':<15} {'Montant':>10}"
        sub_header_individus = f"{'Catégorie':<25} {'Fournisseur':<20} {'Montant':>10}"
        self.resultat_text.insert(tk.END, f"{sub_header_falaise}  |  {sub_header_individus}\n")
        self.resultat_text.insert(tk.END, "-" * 70 + "  |  " + "-" * 70 + "\n")
        
        # Afficher les données côte à côte
        max_lignes = max(len(lignes_falaise), len(lignes_individus))
        for i in range(max_lignes):
            ligne_falaise = lignes_falaise[i] if i < len(lignes_falaise) else " " * 70
            ligne_individus = lignes_individus[i] if i < len(lignes_individus) else " " * 70
            self.resultat_text.insert(tk.END, f"{ligne_falaise:<70}  |  {ligne_individus:<70}\n")
        
        # Totaux
        self.resultat_text.insert(tk.END, "-" * 70 + "  |  " + "-" * 70 + "\n")
        total_falaise_str = f"{'TOTAL FALAISE:':<55} {total_falaise:>10.2f} TND"
        total_individus_str = f"{'TOTAL INDIVIDUS:':<50} {total_individus:>10.2f} TND"
        self.resultat_text.insert(tk.END, f"{total_falaise_str:<70}  |  {total_individus_str:<70}\n")
        
        # === REVENUS (format horizontal) ===
        self.resultat_text.insert(tk.END, "\n" + "=" * 180 + "\n")
        self.resultat_text.insert(tk.END, "📥 REVENUS\n")
        self.resultat_text.insert(tk.END, "=" * 180 + "\n")
        
        if revenus_tries:
            # En-tête des dates
            header_rev = "Date      |"
            for date_key, _ in revenus_tries:
                header_rev += f" {date_key:>8} |"
            self.resultat_text.insert(tk.END, header_rev + "\n")
            self.resultat_text.insert(tk.END, "-" * len(header_rev) + "\n")
            
            # Ligne des montants
            montants_line = "Montant   |"
            total_revenus = 0
            for date_key, data_dict in revenus_tries:
                montant = data_dict['montant']
                montants_line += f" {montant:>8.2f} |"
                total_revenus += montant
            
            self.resultat_text.insert(tk.END, montants_line + "\n")
            self.resultat_text.insert(tk.END, "-" * len(header_rev) + "\n")
            self.resultat_text.insert(tk.END, f"TOTAL REVENUS: {total_revenus:.2f} TND\n")
        else:
            self.resultat_text.insert(tk.END, "Aucun revenu trouvé pour cette période.\n")
            total_revenus = 0
        
        # === BILAN ===
        self.resultat_text.insert(tk.END, "\n" + "=" * 180 + "\n")
        self.resultat_text.insert(tk.END, "💰 BILAN FINANCIER\n")
        self.resultat_text.insert(tk.END, "=" * 180 + "\n")
        
        total_depenses = total_falaise + total_individus
        benefice = total_revenus - total_depenses
        
        self.resultat_text.insert(tk.END, f"{'Total Revenus:':<50} {total_revenus:>20.2f} TND\n")
        self.resultat_text.insert(tk.END, f"{'Total Dépenses Falaise:':<50} {total_falaise:>20.2f} TND\n")
        self.resultat_text.insert(tk.END, f"{'Total Dépenses Individus:':<50} {total_individus:>20.2f} TND\n")
        self.resultat_text.insert(tk.END, f"{'Total Dépenses:':<50} {total_depenses:>20.2f} TND\n")
        self.resultat_text.insert(tk.END, "-" * 180 + "\n")
        
        if benefice >= 0:
            self.resultat_text.insert(tk.END, f"{'✅ BÉNÉFICE:':<50} {benefice:>20.2f} TND\n")
        else:
            self.resultat_text.insert(tk.END, f"{'❌ PERTE:':<50} {abs(benefice):>20.2f} TND\n")
    
    def afficher_section_depenses(self, donnees):
        """Affiche la section dépenses et retourne le total"""
        if not donnees:
            self.resultat_text.insert(tk.END, "Aucune dépense trouvée pour cette période.\n")
            return 0.0
        
        # Regrouper les données
        donnees_groupees = {}
        for donnee in donnees:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in donnees_groupees:
                donnees_groupees[cle] = 0
            donnees_groupees[cle] += montant
        
        # Afficher l'en-tête
        header = f"{'Type Dépense':<20} {'Catégorie':<25} {'Fournisseur':<25} {'Montant (TND)':<20}\n"
        self.resultat_text.insert(tk.END, header)
        self.resultat_text.insert(tk.END, "-" * 92 + "\n")
        
        # Organiser et afficher
        donnees_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(donnees_groupees.items()):
            if type_dep not in donnees_organisees:
                donnees_organisees[type_dep] = {}
            if source not in donnees_organisees[type_dep]:
                donnees_organisees[type_dep][source] = []
            donnees_organisees[type_dep][source].append((categorie_item, montant_total))
        
        total = 0
        for type_dep in sorted(donnees_organisees.keys()):
            type_printed = False
            for source in sorted(donnees_organisees[type_dep].keys()):
                source_printed = False
                categories = donnees_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    type_str = type_dep if not type_printed else ""
                    source_str = source if not source_printed else ""
                    
                    ligne = f"{type_str:<20} {categorie_item:<25} {source_str:<25} {montant_total:<20.2f}\n"
                    self.resultat_text.insert(tk.END, ligne)
                    total += montant_total
                    
                    if not type_printed:
                        type_printed = True
                    if not source_printed:
                        source_printed = True
        
        self.resultat_text.insert(tk.END, "-" * 92 + "\n")
        self.resultat_text.insert(tk.END, f"{'TOTAL DÉPENSES:':<72} {total:<20.2f} TND\n")
        
        return total
    
    def afficher_section_revenus(self, donnees):
        """Affiche la section revenus et retourne le total"""
        if not donnees:
            self.resultat_text.insert(tk.END, "Aucun revenu trouvé pour cette période.\n")
            return 0.0
        
        # Regrouper les données
        donnees_groupees = {}
        for donnee in donnees:
            date_str, montant, source, categorie_item = donnee
            cle = (categorie_item, source)
            if cle not in donnees_groupees:
                donnees_groupees[cle] = 0
            donnees_groupees[cle] += montant
        
        # Afficher l'en-tête
        header = f"{'Catégorie':<30} {'Source':<30} {'Montant (TND)':<20}\n"
        self.resultat_text.insert(tk.END, header)
        self.resultat_text.insert(tk.END, "-" * 82 + "\n")
        
        # Organiser et afficher
        donnees_organisees = {}
        for (categorie_item, source), montant_total in sorted(donnees_groupees.items()):
            if categorie_item not in donnees_organisees:
                donnees_organisees[categorie_item] = []
            donnees_organisees[categorie_item].append((source, montant_total))
        
        total = 0
        for categorie_item in sorted(donnees_organisees.keys()):
            cat_printed = False
            for source, montant_total in donnees_organisees[categorie_item]:
                cat_str = categorie_item if not cat_printed else ""
                
                ligne = f"{cat_str:<30} {source:<30} {montant_total:<20.2f}\n"
                self.resultat_text.insert(tk.END, ligne)
                total += montant_total
                
                if not cat_printed:
                    cat_printed = True
        
        self.resultat_text.insert(tk.END, "-" * 82 + "\n")
        self.resultat_text.insert(tk.END, f"{'TOTAL REVENUS:':<62} {total:<20.2f} TND\n")
        
        return total
    
    def afficher_rapport_depenses(self, donnees, categorie, periode, date_ref):
        """Affiche le rapport des dépenses uniquement"""
        titre = f"Rapport de Dépenses de {categorie} {self.formater_periode(periode, date_ref)}"
        self.resultat_text.insert(tk.END, titre + "\n\n")
        
        if not donnees:
            self.resultat_text.insert(tk.END, "Aucune donnée trouvée pour cette période.\n")
            return
        
        # Afficher avec la logique existante
        donnees_groupees = {}
        for donnee in donnees:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in donnees_groupees:
                donnees_groupees[cle] = 0
            donnees_groupees[cle] += montant
        
        periode_affichage = self.formater_periode(periode, date_ref)
        self.resultat_text.insert(tk.END, f"Période: {periode_affichage}\n\n")
        
        header = f"{'Type Dépense':<20} {'Catégorie':<25} {'Fournisseur':<25} {'Montant Total (TND)':<20}\n"
        separator = "-" * 92 + "\n"
        self.resultat_text.insert(tk.END, header)
        self.resultat_text.insert(tk.END, separator)
        
        donnees_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(donnees_groupees.items()):
            if type_dep not in donnees_organisees:
                donnees_organisees[type_dep] = {}
            if source not in donnees_organisees[type_dep]:
                donnees_organisees[type_dep][source] = []
            donnees_organisees[type_dep][source].append((categorie_item, montant_total))
        
        total_general = 0
        for type_dep in sorted(donnees_organisees.keys()):
            type_printed = False
            for source in sorted(donnees_organisees[type_dep].keys()):
                source_printed = False
                categories = donnees_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    type_str = type_dep if not type_printed else ""
                    source_str = source if not source_printed else ""
                    
                    ligne = f"{type_str:<20} {categorie_item:<25} {source_str:<25} {montant_total:<20.2f}\n"
                    self.resultat_text.insert(tk.END, ligne)
                    total_general += montant_total
                    
                    if not type_printed:
                        type_printed = True
                    if not source_printed:
                        source_printed = True
        
        self.resultat_text.insert(tk.END, separator)
        self.resultat_text.insert(tk.END, f"\n{'TOTAL GÉNÉRAL:':<72} {total_general:<20.2f} TND\n")
    
    def afficher_rapport_revenus(self, donnees, categorie, periode, date_ref):
        """Affiche le rapport des revenus avec dates en horizontal"""
        titre = f"Rapport de Revenus de {categorie} {self.formater_periode(periode, date_ref)}"
        self.resultat_text.insert(tk.END, titre + "\n\n")
        
        if not donnees:
            self.resultat_text.insert(tk.END, "Aucune donnée trouvée pour cette période.\n")
            return
        
        # Regrouper par date
        donnees_par_date = {}
        for donnee in donnees:
            date_str, montant, source, categorie_item = donnee
            try:
                jour, mois, annee = date_str.split('/')
                date_key = f"{jour}/{mois}"
                date_obj = datetime(int(annee), int(mois), int(jour))
            except:
                date_key = date_str
                date_obj = datetime.now()
            
            if date_key not in donnees_par_date:
                donnees_par_date[date_key] = {'montant': 0, 'date_obj': date_obj}
            donnees_par_date[date_key]['montant'] += montant
        
        # Trier par date
        donnees_triees = sorted(donnees_par_date.items(), key=lambda x: x[1]['date_obj'])
        
        periode_affichage = self.formater_periode(periode, date_ref)
        self.resultat_text.insert(tk.END, f"Période: {periode_affichage}\n\n")
        
        # Affichage horizontal
        # En-tête des dates
        header = "Date      |"
        for date_key, _ in donnees_triees:
            header += f" {date_key:>8} |"
        self.resultat_text.insert(tk.END, header + "\n")
        self.resultat_text.insert(tk.END, "-" * len(header) + "\n")
        
        # Ligne des montants
        montants_line = "Montant   |"
        total_general = 0
        for date_key, data_dict in donnees_triees:
            montant = data_dict['montant']
            montants_line += f" {montant:>8.2f} |"
            total_general += montant
        
        self.resultat_text.insert(tk.END, montants_line + "\n")
        self.resultat_text.insert(tk.END, "-" * len(header) + "\n")
        
        # Total
        self.resultat_text.insert(tk.END, f"\nTOTAL GÉNÉRAL: {total_general:.2f} TND\n")
    
    def formater_periode(self, periode, date_ref):
        """Formate la période pour le titre"""
        if periode == "Jour":
            return f"du {date_ref.strftime('%d/%m/%Y')}"
        elif periode == "Semaine":
            start_of_week = date_ref
            end_of_week = start_of_week + timedelta(days=6)
            return f"semaine du {start_of_week.strftime('%d/%m/%Y')} au {end_of_week.strftime('%d/%m/%Y')}"
        elif periode == "Mois":
            return f"du mois de {date_ref.strftime('%B %Y').capitalize()}"
        elif periode == "Année":
            return f"Année {date_ref.year}"
        return ""

    def get_depenses_filtrees(self, categorie, date_ref, periode, type_depense):
        """Récupère les dépenses filtrées avec toutes les informations"""
        conn = database.connect_db()
        cursor = conn.cursor()
        query = """
            SELECT date, montant, fournisseur, categorie, type_depense
            FROM depenses 
            WHERE compte = ?
        """
        params = [self.compte_actif]
        
        # Filtre par type de dépense
        if type_depense != "TOUT":
            query += " AND type_depense = ?"
            params.append(type_depense)
        
        # Filtre par catégorie
        if not categorie.startswith("Tout"):
            query += " AND categorie = ?"
            params.append(categorie)
        
        # Filtre par période
        if periode == "Jour":
            query += " AND date = ?"
            params.append(date_ref.strftime("%Y-%m-%d"))
        elif periode == "Semaine":
            start = date_ref
            end = start + timedelta(days=6)
            query += " AND date BETWEEN ? AND ?"
            params.extend([start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])
        elif periode == "Mois":
            start = date_ref.replace(day=1)
            end = (start.replace(month=start.month % 12 + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)) - timedelta(days=1)
            query += " AND date BETWEEN ? AND ?"
            params.extend([start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])
        elif periode == "Année":
            start = date_ref.replace(month=1, day=1)
            end = date_ref.replace(month=12, day=31)
            query += " AND date BETWEEN ? AND ?"
            params.extend([start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])

        query += " ORDER BY date DESC, categorie, fournisseur"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            date_str = row[0]
            montant = row[1]
            fournisseur = row[2] or "-"
            categorie_item = row[3] or "-"
            type_dep = row[4] or "-"
            
            # Convertir YYYY-MM-DD → DD/MM/YYYY
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%d/%m/%Y")
            except Exception:
                formatted_date = "Date invalide"
            
            result.append((formatted_date, montant, fournisseur, categorie_item, type_dep))
        
        return result

    def get_revenus_filtres(self, categorie, date_ref, periode):
        """Récupère les revenus filtrés avec toutes les informations"""
        conn = database.connect_db()
        cursor = conn.cursor()
        query = """
            SELECT date, montant, source, source as categorie_display
            FROM revenus 
            WHERE compte = ?
        """
        params = [self.compte_actif]
        
        if not categorie.startswith("Tout"):
            query += " AND source = ?"
            params.append(categorie)
        
        # Filtre par période
        if periode == "Jour":
            query += " AND date = ?"
            params.append(date_ref.strftime("%Y-%m-%d"))
        elif periode == "Semaine":
            start = date_ref
            end = start + timedelta(days=6)
            query += " AND date BETWEEN ? AND ?"
            params.extend([start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])
        elif periode == "Mois":
            start = date_ref.replace(day=1)
            end = (start.replace(month=start.month % 12 + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)) - timedelta(days=1)
            query += " AND date BETWEEN ? AND ?"
            params.extend([start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])
        elif periode == "Année":
            start = date_ref.replace(month=1, day=1)
            end = date_ref.replace(month=12, day=31)
            query += " AND date BETWEEN ? AND ?"
            params.extend([start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])

        query += " ORDER BY date DESC, source"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            date_str = row[0]
            montant = row[1]
            source = row[2] or "-"
            categorie_item = row[3] or "-"
            
            # Convertir YYYY-MM-DD → DD/MM/YYYY
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%d/%m/%Y")
            except Exception:
                formatted_date = "Date invalide"
            
            result.append((formatted_date, montant, source, categorie_item))
        
        return result

    def exporter_excel(self):
        """Exporte le rapport en Excel (.xlsx) avec mise en forme"""
        type_val = self.type_var.get()
        categorie = self.categorie_var.get()
        periode = self.periode_selectionnee
        date_ref = self.date_selectionnee

        if type_val != "TOUT" and not categorie:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une catégorie.")
            return

        if type_val == "TOUT":
            if categorie == "2 à 2":
                self.exporter_excel_2a2(periode, date_ref)
            else:
                self.exporter_excel_complet(periode, date_ref)
        elif type_val == "Dépenses":
            type_depense = self.type_depense_var.get()
            donnees = self.get_depenses_filtrees(categorie, date_ref, periode, type_depense)
            if not donnees:
                messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
                return
            self.exporter_excel_depenses(donnees, categorie, periode, date_ref)
        else:
            donnees = self.get_revenus_filtres(categorie, date_ref, periode)
            if not donnees:
                messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
                return
            self.exporter_excel_revenus(donnees, categorie, periode, date_ref)

    def exporter_excel_complet(self, periode, date_ref):
        """Exporte le rapport complet (Dépenses + Revenus) en Excel"""
        # Récupérer les données
        donnees_depenses = self.get_depenses_filtrees("Tout(e)s les Dépenses", date_ref, periode, "TOUT")
        donnees_revenus = self.get_revenus_filtres("Tout(e)s les Revenus", date_ref, periode)
        
        if not donnees_depenses and not donnees_revenus:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Fichiers Excel", "*.xlsx"), ("Tous les fichiers", "*.*")],
            title=f"Exporter Rapport Complet - {self.formater_periode(periode, date_ref)}"
        )
        
        if not filename:
            return
        
        # Créer le workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Rapport Complet"
        
        # Styles
        titre_font = Font(name='Arial', size=16, bold=True)
        header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='808080', end_color='808080', fill_type='solid')
        data_fill = PatternFill(start_color='F5F5DC', end_color='F5F5DC', fill_type='solid')
        total_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
        bilan_fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
        perte_fill = PatternFill(start_color='FFB6C1', end_color='FFB6C1', fill_type='solid')
        total_font = Font(name='Arial', size=11, bold=True)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        center_align = Alignment(horizontal='center', vertical='center')
        right_align = Alignment(horizontal='right', vertical='center')
        
        # Titre
        periode_affichage = self.formater_periode(periode, date_ref)
        titre = f"Rapport Complet - {periode_affichage}"
        ws.merge_cells('A1:G1')
        cell = ws['A1']
        cell.value = titre
        cell.font = titre_font
        cell.alignment = center_align
        
        row_idx = 3
        
        # Regrouper et organiser les dépenses
        depenses_groupees = {}
        for donnee in donnees_depenses:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in depenses_groupees:
                depenses_groupees[cle] = 0
            depenses_groupees[cle] += montant
        
        dep_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(depenses_groupees.items()):
            if type_dep not in dep_organisees:
                dep_organisees[type_dep] = {}
            if source not in dep_organisees[type_dep]:
                dep_organisees[type_dep][source] = []
            dep_organisees[type_dep][source].append((categorie_item, montant_total))
        
        # Regrouper les revenus par date
        revenus_par_date = {}
        for donnee in donnees_revenus:
            date_str, montant, source, categorie_item = donnee
            # date_str est au format DD/MM/YYYY
            try:
                jour, mois, annee = date_str.split('/')
                date_key = f"{jour}/{mois}"
                date_obj = datetime(int(annee), int(mois), int(jour))
            except:
                date_key = date_str
                date_obj = datetime.now()
            
            if date_key not in revenus_par_date:
                revenus_par_date[date_key] = {'montant': 0, 'date_obj': date_obj}
            revenus_par_date[date_key]['montant'] += montant

        # Trier par date
        revenus_tries = sorted(revenus_par_date.items(), key=lambda x: x[1]['date_obj'])
        
        # En-têtes DÉPENSES
        ws.cell(row=row_idx, column=1).value = "DÉPENSES"
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=4)
        ws.cell(row=row_idx, column=1).font = header_font
        ws.cell(row=row_idx, column=1).fill = header_fill
        ws.cell(row=row_idx, column=1).alignment = center_align
        ws.cell(row=row_idx, column=1).border = border
        
        # En-têtes REVENUS
        ws.cell(row=row_idx, column=6).value = "REVENUS"
        ws.merge_cells(start_row=row_idx, start_column=6, end_row=row_idx, end_column=8)
        ws.cell(row=row_idx, column=6).font = header_font
        ws.cell(row=row_idx, column=6).fill = header_fill
        ws.cell(row=row_idx, column=6).alignment = center_align
        ws.cell(row=row_idx, column=6).border = border
        
        row_idx += 1
        
        # Sous-en-têtes dépenses
        headers_dep = ["Type", "Catégorie", "Fournisseur", "Montant (TND)"]
        for col_idx, header in enumerate(headers_dep, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = header
            cell.font = Font(name='Arial', size=10, bold=True)
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_align
        
        # Sous-en-têtes revenus
        headers_rev = ["Date", "Montant (TND)"]
        for col_idx, header in enumerate(headers_rev, start=6):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = header
            cell.font = Font(name='Arial', size=10, bold=True)
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_align
        
        start_data_row = row_idx + 1
        row_idx_dep = start_data_row
        row_idx_rev = start_data_row
        
        # Écrire les dépenses
        total_depenses = 0
        for type_dep in sorted(dep_organisees.keys()):
            start_type_row = row_idx_dep
            
            for source in sorted(dep_organisees[type_dep].keys()):
                start_source_row = row_idx_dep
                categories = dep_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    # Type
                    cell = ws.cell(row=row_idx_dep, column=1)
                    if i == 0 and row_idx_dep == start_type_row:
                        cell.value = type_dep
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    # Catégorie
                    cell = ws.cell(row=row_idx_dep, column=2)
                    cell.value = categorie_item
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    # Fournisseur
                    cell = ws.cell(row=row_idx_dep, column=3)
                    if i == 0:
                        cell.value = source
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    # Montant
                    cell = ws.cell(row=row_idx_dep, column=4)
                    cell.value = montant_total
                    cell.number_format = '0.00'
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    total_depenses += montant_total
                    row_idx_dep += 1
                
                # Fusionner fournisseur
                if len(categories) > 1:
                    ws.merge_cells(start_row=start_source_row, start_column=3,
                                end_row=row_idx_dep-1, end_column=3)
            
            # Fusionner type
            if row_idx_dep - start_type_row > 1:
                ws.merge_cells(start_row=start_type_row, start_column=1,
                            end_row=row_idx_dep-1, end_column=1)
        
        # Écrire les revenus
        total_revenus = 0
        for date_key, data_dict in revenus_tries:
            montant = data_dict['montant']
            
            # Date
            cell = ws.cell(row=row_idx_rev, column=6)
            cell.value = date_key
            cell.fill = data_fill
            cell.border = border
            cell.alignment = center_align
            
            # Montant
            cell = ws.cell(row=row_idx_rev, column=7)
            cell.value = montant
            cell.number_format = '0.00'
            cell.fill = data_fill
            cell.border = border
            cell.alignment = center_align
            
            total_revenus += montant
            row_idx_rev += 1
        
        
        # Total des dépenses
        max_row = max(row_idx_dep, row_idx_rev)
        ws.merge_cells(start_row=max_row, start_column=1, end_row=max_row, end_column=3)
        cell = ws.cell(row=max_row, column=1)
        cell.value = "TOTAL DÉPENSES:"
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = right_align
        
        cell = ws.cell(row=max_row, column=4)
        cell.value = total_depenses
        cell.number_format = '0.00'
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = center_align
        
        # Total des revenus
        cell = ws.cell(row=max_row, column=6)
        cell.value = "TOTAL REVENUS:"
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = right_align
        
        cell = ws.cell(row=max_row, column=8)
        cell.value = total_revenus
        cell.number_format = '0.00'
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = center_align
        
        # BILAN
        bilan_row = max_row + 2
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=8)
        cell = ws.cell(row=bilan_row, column=1)
        cell.value = "BILAN FINANCIER"
        cell.font = Font(name='Arial', size=14, bold=True)
        cell.alignment = center_align
        
        benefice = total_revenus - total_depenses
        
        bilan_row += 1
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=5)
        cell = ws.cell(row=bilan_row, column=1)
        cell.value = "Total Revenus:"
        cell.font = total_font
        cell.alignment = right_align
        
        cell = ws.cell(row=bilan_row, column=6)
        cell.value = total_revenus
        cell.number_format = '0.00'
        cell.font = total_font
        cell.alignment = center_align
        
        bilan_row += 1
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=5)
        cell = ws.cell(row=bilan_row, column=1)
        cell.value = "Total Dépenses:"
        cell.font = total_font
        cell.alignment = right_align
        
        cell = ws.cell(row=bilan_row, column=6)
        cell.value = total_depenses
        cell.number_format = '0.00'
        cell.font = total_font
        cell.alignment = center_align
        
        bilan_row += 1
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=5)
        cell = ws.cell(row=bilan_row, column=1)
        if benefice >= 0:
            cell.value = "✅ BÉNÉFICE:"
            fill_color = bilan_fill
        else:
            cell.value = "❌ PERTE:"
            fill_color = perte_fill
        cell.font = Font(name='Arial', size=12, bold=True)
        cell.fill = fill_color
        cell.alignment = right_align
        cell.border = border
        
        cell = ws.cell(row=bilan_row, column=6)
        cell.value = abs(benefice)
        cell.number_format = '0.00'
        cell.font = Font(name='Arial', size=12, bold=True)
        cell.fill = fill_color
        cell.alignment = center_align
        cell.border = border
        
        self.ajuster_largeur_colonnes_excel(ws)
        
        wb.save(filename)
        messagebox.showinfo("Export réussi", f"Fichier Excel exporté : {filename}")
     
    def exporter_excel_revenus(self, donnees, categorie, periode, date_ref):
        """Exporte uniquement les revenus en Excel avec format Date/Montant"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Fichiers Excel", "*.xlsx"), ("Tous les fichiers", "*.*")],
            title=f"Exporter Revenus - {categorie} - {self.formater_periode(periode, date_ref)}"
        )
        
        if not filename:
            return
        
        # Regrouper par date
        donnees_par_date = {}
        for donnee in donnees:
            date_str, montant, source, categorie_item = donnee
            # Convertir DD/MM/YYYY en objet date pour tri
            try:
                jour, mois, annee = date_str.split('/')
                date_obj = datetime(int(annee), int(mois), int(jour))
                date_key = f"{jour}/{mois}"  # Format JJ/MM
            except:
                date_key = date_str
                date_obj = datetime.now()
            
            if date_key not in donnees_par_date:
                donnees_par_date[date_key] = {'montant': 0, 'date_obj': date_obj}
            donnees_par_date[date_key]['montant'] += montant
        
        # Trier par date
        donnees_triees = sorted(donnees_par_date.items(), key=lambda x: x[1]['date_obj'])
        
        # Créer le workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Revenus"
        
        # Styles
        titre_font = Font(name='Arial', size=16, bold=True)
        header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='808080', end_color='808080', fill_type='solid')
        data_fill = PatternFill(start_color='F5F5DC', end_color='F5F5DC', fill_type='solid')
        total_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
        total_font = Font(name='Arial', size=11, bold=True)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        center_align = Alignment(horizontal='center', vertical='center')
        
        # Titre
        periode_affichage = self.formater_periode(periode, date_ref)
        titre = f"Rapport de Revenus - {categorie} - {periode_affichage}"
        ws.merge_cells('A1:B1')
        cell = ws['A1']
        cell.value = titre
        cell.font = titre_font
        cell.alignment = center_align
        
        # En-têtes
        row_idx = 3
        headers = ["Date", "Montant (TND)"]
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_align
        
        # Données
        row_idx += 1
        total_general = 0
        
        for date_key, data in donnees_triees:
            montant = data['montant']
            
            # Date
            cell = ws.cell(row=row_idx, column=1)
            cell.value = date_key
            cell.fill = data_fill
            cell.border = border
            cell.alignment = center_align
            
            # Montant
            cell = ws.cell(row=row_idx, column=2)
            cell.value = montant
            cell.number_format = '0.00'
            cell.fill = data_fill
            cell.border = border
            cell.alignment = center_align
            
            total_general += montant
            row_idx += 1
        
        # Total
        cell = ws.cell(row=row_idx, column=1)
        cell.value = "TOTAL GÉNÉRAL:"
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = center_align
        
        cell = ws.cell(row=row_idx, column=2)
        cell.value = total_general
        cell.number_format = '0.00'
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = center_align
        
        self.ajuster_largeur_colonnes_excel(ws)
        
        wb.save(filename)
        messagebox.showinfo("Export réussi", f"Fichier Excel exporté : {filename}")
    
    def exporter_pdf(self):
        """Exporte le rapport en PDF"""
        type_val = self.type_var.get()
        categorie = self.categorie_var.get()
        periode = self.periode_selectionnee
        date_ref = self.date_selectionnee

        if type_val != "TOUT" and not categorie:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une catégorie.")
            return

        if type_val == "TOUT":
            if categorie == "2 à 2":
                self.exporter_pdf_2a2(periode, date_ref)
            else:
                self.exporter_pdf_complet(periode, date_ref)
        elif type_val == "Dépenses":
            type_depense = self.type_depense_var.get()
            donnees = self.get_depenses_filtrees(categorie, date_ref, periode, type_depense)
            if not donnees:
                messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
                return
            self.exporter_pdf_depenses(donnees, categorie, periode, date_ref)
        else:
            donnees = self.get_revenus_filtres(categorie, date_ref, periode)
            if not donnees:
                messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
                return
            self.exporter_pdf_revenus(donnees, categorie, periode, date_ref)
    
    def exporter_pdf_complet(self, periode, date_ref):
        """Exporte le rapport complet (Dépenses + Revenus) en PDF"""
        # Récupérer les données
        donnees_depenses = self.get_depenses_filtrees("Tout(e)s les Dépenses", date_ref, periode, "TOUT")
        donnees_revenus = self.get_revenus_filtres("Tout(e)s les Revenus", date_ref, periode)
        
        if not donnees_depenses and not donnees_revenus:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")],
            title=f"Exporter Rapport Complet - {self.formater_periode(periode, date_ref)}"
        )
        
        if not filename:
            return
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1
        )
        style_subtitle = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=13,
            spaceAfter=15,
            alignment=1
        )
        style_normal = styles['Normal']
        
        elements = []
        
        # Titre
        periode_affichage = self.formater_periode(periode, date_ref)
        titre = f"Rapport Complet - {periode_affichage}"
        elements.append(Paragraph(titre, style_title))
        elements.append(Spacer(1, 20))
        
        # Regrouper et organiser les dépenses
        depenses_groupees = {}
        for donnee in donnees_depenses:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in depenses_groupees:
                depenses_groupees[cle] = 0
            depenses_groupees[cle] += montant
        
        dep_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(depenses_groupees.items()):
            if type_dep not in dep_organisees:
                dep_organisees[type_dep] = {}
            if source not in dep_organisees[type_dep]:
                dep_organisees[type_dep][source] = []
            dep_organisees[type_dep][source].append((categorie_item, montant_total))
        
       # Regrouper les revenus par date
        revenus_par_date = {}
        for donnee in donnees_revenus:
            date_str, montant, source, categorie_item = donnee
            # date_str est au format DD/MM/YYYY
            try:
                jour, mois, annee = date_str.split('/')
                date_key = f"{jour}/{mois}"
                date_obj = datetime(int(annee), int(mois), int(jour))
            except:
                date_key = date_str
                date_obj = datetime.now()
            
            if date_key not in revenus_par_date:
                revenus_par_date[date_key] = {'montant': 0, 'date_obj': date_obj}
            revenus_par_date[date_key]['montant'] += montant

        # Trier par date
        revenus_tries = sorted(revenus_par_date.items(), key=lambda x: x[1]['date_obj'])
        
        # === TABLEAU DÉPENSES ===
        elements.append(Paragraph("📤 DÉPENSES", style_subtitle))
        elements.append(Spacer(1, 10))
        
        data_dep = [["Type Dépense", "Catégorie", "Fournisseur", "Montant (TND)"]]
        table_styles_dep = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        row_idx_dep = 1
        total_depenses = 0
        
        for type_dep in sorted(dep_organisees.keys()):
            start_type_row = row_idx_dep
            nb_rows_for_type = 0
            
            for source in sorted(dep_organisees[type_dep].keys()):
                start_source_row = row_idx_dep
                categories = dep_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    if i == 0 and row_idx_dep == start_type_row:
                        data_dep.append([type_dep, categorie_item, source, f"{montant_total:.2f}"])
                    elif i == 0:
                        data_dep.append(["", categorie_item, source, f"{montant_total:.2f}"])
                    else:
                        data_dep.append(["", categorie_item, "", f"{montant_total:.2f}"])
                    
                    total_depenses += montant_total
                    row_idx_dep += 1
                    nb_rows_for_type += 1
                
                if len(categories) > 1:
                    table_styles_dep.append(('SPAN', (2, start_source_row), (2, row_idx_dep - 1)))
            
            if nb_rows_for_type > 1:
                table_styles_dep.append(('SPAN', (0, start_type_row), (0, start_type_row + nb_rows_for_type - 1)))
        
        # Total dépenses
        data_dep.append(["TOTAL DÉPENSES:", "", "", f"{total_depenses:.2f}"])
        table_styles_dep.append(('SPAN', (0, row_idx_dep), (2, row_idx_dep)))
        table_styles_dep.append(('BACKGROUND', (0, row_idx_dep), (-1, row_idx_dep), colors.lightgrey))
        table_styles_dep.append(('FONTNAME', (0, row_idx_dep), (-1, row_idx_dep), 'Helvetica-Bold'))
        table_styles_dep.append(('ALIGN', (0, row_idx_dep), (2, row_idx_dep), 'RIGHT'))
        
        table_dep = Table(data_dep, colWidths=[100, 120, 120, 100])
        table_dep.setStyle(TableStyle(table_styles_dep))
        elements.append(table_dep)
        elements.append(Spacer(1, 30))
        
        # === TABLEAU REVENUS ===
        elements.append(Paragraph("📥 REVENUS", style_subtitle))
        elements.append(Spacer(1, 10))

        data_rev = [["Date", "Montant (TND)"]]
        table_styles_rev = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        total_revenus = 0

        for date_key, data_dict in revenus_tries:
            montant = data_dict['montant']
            data_rev.append([date_key, f"{montant:.2f}"])
            total_revenus += montant

        # Total revenus
        row_idx_rev = len(data_rev)
        data_rev.append(["TOTAL REVENUS:", f"{total_revenus:.2f}"])
        table_styles_rev.append(('BACKGROUND', (0, row_idx_rev), (-1, row_idx_rev), colors.lightgrey))
        table_styles_rev.append(('FONTNAME', (0, row_idx_rev), (-1, row_idx_rev), 'Helvetica-Bold'))

        table_rev = Table(data_rev, colWidths=[200, 200])
        table_rev.setStyle(TableStyle(table_styles_rev))
        elements.append(table_rev)
        elements.append(Spacer(1, 30))
        
        # === BILAN ===
        elements.append(Paragraph("💰 BILAN FINANCIER", style_subtitle))
        elements.append(Spacer(1, 10))
        
        benefice = total_revenus - total_depenses
        
        data_bilan = [
            ["Total Revenus:", f"{total_revenus:.2f} TND"],
            ["Total Dépenses:", f"{total_depenses:.2f} TND"],
        ]
        
        if benefice >= 0:
            data_bilan.append(["✅ BÉNÉFICE:", f"{benefice:.2f} TND"])
            color_bilan = colors.lightgreen
        else:
            data_bilan.append(["❌ PERTE:", f"{abs(benefice):.2f} TND"])
            color_bilan = colors.lightpink
        
        table_bilan = Table(data_bilan, colWidths=[200, 150])
        table_bilan.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 1), colors.beige),
            ('BACKGROUND', (0, 2), (-1, 2), color_bilan),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(table_bilan)
        
        doc.build(elements)
        messagebox.showinfo("Export réussi", f"Rapport PDF exporté : {filename}")

    def exporter_excel_2a2(self, periode, date_ref):
        """Exporte le rapport 2 à 2 en Excel"""
        # Demander où sauvegarder le fichier
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Fichiers Excel", "*.xlsx"), ("Tous les fichiers", "*.*")],
            title=f"Exporter Rapport 2 à 2 - {self.formater_periode(periode, date_ref)}"
        )
        
        if not filename:
            return
        
        # Récupérer les filtres
        filtre_falaise = self.depenses_falaise_var.get()
        filtre_individus = self.depenses_individus_var.get()
        
        # Récupérer les données
        if filtre_falaise == "TOUT":
            donnees_falaise = []
            for type_dep in ["FIXES", "VARIABLES", "INTERMEDIAIRES"]:
                donnees_falaise.extend(
                    self.get_depenses_filtrees("Tout(e)s les Dépenses", date_ref, periode, type_dep)
                )
        else:
            donnees_falaise = self.get_depenses_filtrees(
                "Tout(e)s les Dépenses", date_ref, periode, filtre_falaise
            )
        
        if filtre_individus == "TOUT":
            donnees_individus = self.get_depenses_filtrees(
                "Tout(e)s les Dépenses", date_ref, periode, "INDIVIDUS"
            )
        else:
            donnees_individus = [
                d for d in self.get_depenses_filtrees(
                    "Tout(e)s les Dépenses", date_ref, periode, "INDIVIDUS"
                )
                if d[3] == filtre_individus
            ]
        
        donnees_revenus = self.get_revenus_filtres("Tout(e)s les Revenus", date_ref, periode)
        
        # Créer le workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Rapport 2 à 2"
        
        # Styles
        titre_font = Font(name='Arial', size=16, bold=True)
        header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='808080', end_color='808080', fill_type='solid')
        data_fill = PatternFill(start_color='F5F5DC', end_color='F5F5DC', fill_type='solid')
        total_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
        bilan_fill = PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid')
        perte_fill = PatternFill(start_color='FFB6C1', end_color='FFB6C1', fill_type='solid')
        revenus_fill = PatternFill(start_color='ADD8E6', end_color='ADD8E6', fill_type='solid')
        total_font = Font(name='Arial', size=11, bold=True)
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        center_align = Alignment(horizontal='center', vertical='center')
        right_align = Alignment(horizontal='right', vertical='center')
        
        # Titre
        periode_affichage = self.formater_periode(periode, date_ref)
        titre = f"Rapport Comparatif 2 à 2 - {periode_affichage}"
        ws.merge_cells('A1:H1')
        cell = ws['A1']
        cell.value = titre
        cell.font = titre_font
        cell.alignment = center_align
        
        row_idx = 3
        
        # Traiter Dépenses Falaise
        depenses_falaise_groupees = {}
        for donnee in donnees_falaise:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in depenses_falaise_groupees:
                depenses_falaise_groupees[cle] = 0
            depenses_falaise_groupees[cle] += montant
        
        falaise_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(depenses_falaise_groupees.items()):
            if type_dep not in falaise_organisees:
                falaise_organisees[type_dep] = {}
            if source not in falaise_organisees[type_dep]:
                falaise_organisees[type_dep][source] = []
            falaise_organisees[type_dep][source].append((categorie_item, montant_total))
        
        # Traiter Dépenses Individus
        depenses_individus_groupees = {}
        for donnee in donnees_individus:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (categorie_item, source)
            if cle not in depenses_individus_groupees:
                depenses_individus_groupees[cle] = 0
            depenses_individus_groupees[cle] += montant
        
        individus_organisees = {}
        for (categorie_item, source), montant_total in sorted(depenses_individus_groupees.items()):
            if categorie_item not in individus_organisees:
                individus_organisees[categorie_item] = []
            individus_organisees[categorie_item].append((source, montant_total))
        
        # Traiter Revenus (format horizontal)
        revenus_par_date = {}
        for donnee in donnees_revenus:
            date_str, montant, source, categorie_item = donnee
            try:
                jour, mois, annee = date_str.split('/')
                date_key = f"{jour}/{mois}"
                date_obj = datetime(int(annee), int(mois), int(jour))
            except:
                date_key = date_str
                date_obj = datetime.now()
            
            if date_key not in revenus_par_date:
                revenus_par_date[date_key] = {'montant': 0, 'date_obj': date_obj}
            revenus_par_date[date_key]['montant'] += montant
        
        revenus_tries = sorted(revenus_par_date.items(), key=lambda x: x[1]['date_obj'])
        
        # === EN-TÊTES DÉPENSES FALAISE ===
        ws.cell(row=row_idx, column=1).value = f"DÉPENSES FALAISE ({filtre_falaise})"
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=4)
        ws.cell(row=row_idx, column=1).font = header_font
        ws.cell(row=row_idx, column=1).fill = header_fill
        ws.cell(row=row_idx, column=1).alignment = center_align
        ws.cell(row=row_idx, column=1).border = border
        
        # === EN-TÊTES DÉPENSES INDIVIDUS ===
        ws.cell(row=row_idx, column=6).value = f"DÉPENSES INDIVIDUS ({filtre_individus})"
        ws.merge_cells(start_row=row_idx, start_column=6, end_row=row_idx, end_column=8)
        ws.cell(row=row_idx, column=6).font = header_font
        ws.cell(row=row_idx, column=6).fill = header_fill
        ws.cell(row=row_idx, column=6).alignment = center_align
        ws.cell(row=row_idx, column=6).border = border
        
        row_idx += 1
        
        # Sous-en-têtes Falaise
        headers_falaise = ["Type", "Catégorie", "Fournisseur", "Montant (TND)"]
        for col_idx, header in enumerate(headers_falaise, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = header
            cell.font = Font(name='Arial', size=10, bold=True)
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_align
        
        # Sous-en-têtes Individus
        headers_individus = ["Catégorie", "Fournisseur", "Montant (TND)"]
        for col_idx, header in enumerate(headers_individus, start=6):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.value = header
            cell.font = Font(name='Arial', size=10, bold=True)
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_align
        
        start_data_row = row_idx + 1
        row_idx_falaise = start_data_row
        row_idx_individus = start_data_row
        
        # === ÉCRIRE DÉPENSES FALAISE ===
        total_falaise = 0
        for type_dep in sorted(falaise_organisees.keys()):
            start_type_row = row_idx_falaise
            
            for source in sorted(falaise_organisees[type_dep].keys()):
                start_source_row = row_idx_falaise
                categories = falaise_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    # Type
                    cell = ws.cell(row=row_idx_falaise, column=1)
                    if i == 0 and row_idx_falaise == start_type_row:
                        cell.value = type_dep
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    # Catégorie
                    cell = ws.cell(row=row_idx_falaise, column=2)
                    cell.value = categorie_item
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    # Fournisseur
                    cell = ws.cell(row=row_idx_falaise, column=3)
                    if i == 0:
                        cell.value = source
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    # Montant
                    cell = ws.cell(row=row_idx_falaise, column=4)
                    cell.value = montant_total
                    cell.number_format = '0.00'
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    total_falaise += montant_total
                    row_idx_falaise += 1
                
                # Fusionner fournisseur
                if len(categories) > 1:
                    ws.merge_cells(start_row=start_source_row, start_column=3,
                                end_row=row_idx_falaise-1, end_column=3)
            
            # Fusionner type
            if row_idx_falaise - start_type_row > 1:
                ws.merge_cells(start_row=start_type_row, start_column=1,
                            end_row=row_idx_falaise-1, end_column=1)
        
        # === ÉCRIRE DÉPENSES INDIVIDUS ===
        total_individus = 0
        for categorie_item in sorted(individus_organisees.keys()):
            start_row = row_idx_individus
            sources_list = individus_organisees[categorie_item]
            
            for i, (source, montant_total) in enumerate(sources_list):
                # Catégorie
                cell = ws.cell(row=row_idx_individus, column=6)
                if i == 0:
                    cell.value = categorie_item
                cell.fill = data_fill
                cell.border = border
                cell.alignment = center_align
                
                # Fournisseur
                cell = ws.cell(row=row_idx_individus, column=7)
                cell.value = source
                cell.fill = data_fill
                cell.border = border
                cell.alignment = center_align
                
                # Montant
                cell = ws.cell(row=row_idx_individus, column=8)
                cell.value = montant_total
                cell.number_format = '0.00'
                cell.fill = data_fill
                cell.border = border
                cell.alignment = center_align
                
                total_individus += montant_total
                row_idx_individus += 1
            
            # Fusionner catégorie
            if len(sources_list) > 1:
                ws.merge_cells(start_row=start_row, start_column=6,
                            end_row=row_idx_individus-1, end_column=6)
        
        # === TOTAUX DÉPENSES ===
        max_row = max(row_idx_falaise, row_idx_individus)
        
        # Total Falaise
        ws.merge_cells(start_row=max_row, start_column=1, end_row=max_row, end_column=3)
        cell = ws.cell(row=max_row, column=1)
        cell.value = "TOTAL FALAISE:"
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = right_align
        
        cell = ws.cell(row=max_row, column=4)
        cell.value = total_falaise
        cell.number_format = '0.00'
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = center_align
        
        # Total Individus
        ws.merge_cells(start_row=max_row, start_column=6, end_row=max_row, end_column=7)
        cell = ws.cell(row=max_row, column=6)
        cell.value = "TOTAL INDIVIDUS:"
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = right_align
        
        cell = ws.cell(row=max_row, column=8)
        cell.value = total_individus
        cell.number_format = '0.00'
        cell.font = total_font
        cell.fill = total_fill
        cell.border = border
        cell.alignment = center_align
        
        # === REVENUS (format horizontal) ===
        revenus_row = max_row + 3
        
        ws.cell(row=revenus_row, column=1).value = "REVENUS"
        ws.cell(row=revenus_row, column=1).font = Font(name='Arial', size=12, bold=True)
        ws.cell(row=revenus_row, column=1).fill = revenus_fill
        ws.cell(row=revenus_row, column=1).alignment = center_align
        ws.cell(row=revenus_row, column=1).border = border
        
        revenus_row += 1
        
        if revenus_tries:
            # Ligne "Date"
            cell = ws.cell(row=revenus_row, column=1)
            cell.value = "Date"
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center_align
            
            col_idx = 2
            for date_key, _ in revenus_tries:
                cell = ws.cell(row=revenus_row, column=col_idx)
                cell.value = date_key
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
                cell.alignment = center_align
                col_idx += 1
            
            revenus_row += 1
            
            # Ligne "Montant"
            cell = ws.cell(row=revenus_row, column=1)
            cell.value = "Montant"
            cell.font = Font(name='Arial', size=10, bold=True)
            cell.fill = data_fill
            cell.border = border
            cell.alignment = center_align
            
            col_idx = 2
            total_revenus = 0
            for date_key, data_dict in revenus_tries:
                montant = data_dict['montant']
                cell = ws.cell(row=revenus_row, column=col_idx)
                cell.value = montant
                cell.number_format = '0.00'
                cell.fill = data_fill
                cell.border = border
                cell.alignment = center_align
                total_revenus += montant
                col_idx += 1
            
            revenus_row += 1
            
            # Total Revenus, conservé dans des cellules distinctes pour rester lisible.
            cell = ws.cell(row=revenus_row, column=1)
            cell.value = "TOTAL REVENUS:"
            cell.font = total_font
            cell.fill = total_fill
            cell.border = border
            cell.alignment = right_align
            
            cell = ws.cell(row=revenus_row, column=2)
            cell.value = total_revenus
            cell.number_format = '0.00'
            cell.font = total_font
            cell.fill = total_fill
            cell.border = border
            cell.alignment = center_align
        else:
            total_revenus = 0
            cell = ws.cell(row=revenus_row, column=1)
            cell.value = "TOTAL REVENUS:"
            cell.font = total_font
            cell.fill = total_fill
            cell.border = border
            cell.alignment = right_align

            cell = ws.cell(row=revenus_row, column=2)
            cell.value = total_revenus
            cell.number_format = '0.00'
            cell.font = total_font
            cell.fill = total_fill
            cell.border = border
            cell.alignment = center_align
            
            cell = ws.cell(row=revenus_row + 1, column=1)
            cell.value = "Aucun revenu trouvé"
            cell.alignment = center_align
            cell.font = Font(name='Arial', size=10, italic=True)
            cell.border = border
            revenus_row += 1
                    
        # === BILAN FINANCIER ===
        bilan_row = revenus_row + 3
        
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=8)
        cell = ws.cell(row=bilan_row, column=1)
        cell.value = "BILAN FINANCIER"
        cell.font = Font(name='Arial', size=14, bold=True)
        cell.alignment = center_align
        
        bilan_row += 1
        
        total_depenses = total_falaise + total_individus
        benefice = total_revenus - total_depenses
        
        # Total Revenus
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=5)
        cell = ws.cell(row=bilan_row, column=1)
        cell.value = "Total Revenus:"
        cell.font = total_font
        cell.alignment = right_align
        
        cell = ws.cell(row=bilan_row, column=6)
        cell.value = total_revenus
        cell.number_format = '0.00'
        cell.font = total_font
        cell.alignment = center_align
        
        bilan_row += 1
        
        # Total Dépenses Falaise
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=5)
        cell = ws.cell(row=bilan_row, column=1)
        cell.value = "Total Dépenses Falaise:"
        cell.font = total_font
        cell.alignment = right_align
        
        cell = ws.cell(row=bilan_row, column=6)
        cell.value = total_falaise
        cell.number_format = '0.00'
        cell.font = total_font
        cell.alignment = center_align
        
        bilan_row += 1
        
        # Total Dépenses Individus
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=5)
        cell = ws.cell(row=bilan_row, column=1)
        cell.value = "Total Dépenses Individus:"
        cell.font = total_font
        cell.alignment = right_align
        
        cell = ws.cell(row=bilan_row, column=6)
        cell.value = total_individus
        cell.number_format = '0.00'
        cell.font = total_font
        cell.alignment = center_align
        
        bilan_row += 1
        
        # Total Dépenses
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=5)
        cell = ws.cell(row=bilan_row, column=1)
        cell.value = "Total Dépenses:"
        cell.font = total_font
        cell.alignment = right_align
        
        cell = ws.cell(row=bilan_row, column=6)
        cell.value = total_depenses
        cell.number_format = '0.00'
        cell.font = total_font
        cell.alignment = center_align
        
        bilan_row += 1
        
        # Bénéfice ou Perte
        ws.merge_cells(start_row=bilan_row, start_column=1, end_row=bilan_row, end_column=5)
        cell = ws.cell(row=bilan_row, column=1)
        if benefice >= 0:
            cell.value = "✅ BÉNÉFICE:"
            fill_color = bilan_fill
        else:
            cell.value = "❌ PERTE:"
            fill_color = perte_fill
        cell.font = Font(name='Arial', size=12, bold=True)
        cell.fill = fill_color
        cell.alignment = right_align
        cell.border = border
        
        cell = ws.cell(row=bilan_row, column=6)
        cell.value = abs(benefice)
        cell.number_format = '0.00'
        cell.font = Font(name='Arial', size=12, bold=True)
        cell.fill = fill_color
        cell.alignment = center_align
        cell.border = border
        
        # La colonne E reste un séparateur entre les deux tableaux.
        ws.column_dimensions['E'].width = 3
        self.ajuster_largeur_colonnes_excel(ws)
        
        # Sauvegarder
        wb.save(filename)
        messagebox.showinfo("Export réussi", f"Fichier Excel exporté : {filename}")
    
    def exporter_pdf_2a2(self, periode, date_ref):
        """Exporte le rapport 2 à 2 en PDF"""
        # Demander où sauvegarder le fichier
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")],
            title=f"Exporter Rapport 2 à 2 - {self.formater_periode(periode, date_ref)}"
        )
        
        if not filename:
            return
        
        # Récupérer les filtres
        filtre_falaise = self.depenses_falaise_var.get()
        filtre_individus = self.depenses_individus_var.get()
        
        # Récupérer les données
        if filtre_falaise == "TOUT":
            donnees_falaise = []
            for type_dep in ["FIXES", "VARIABLES", "INTERMEDIAIRES"]:
                donnees_falaise.extend(
                    self.get_depenses_filtrees("Tout(e)s les Dépenses", date_ref, periode, type_dep)
                )
        else:
            donnees_falaise = self.get_depenses_filtrees(
                "Tout(e)s les Dépenses", date_ref, periode, filtre_falaise
            )
        
        if filtre_individus == "TOUT":
            donnees_individus = self.get_depenses_filtrees(
                "Tout(e)s les Dépenses", date_ref, periode, "INDIVIDUS"
            )
        else:
            donnees_individus = [
                d for d in self.get_depenses_filtrees(
                    "Tout(e)s les Dépenses", date_ref, periode, "INDIVIDUS"
                )
                if d[3] == filtre_individus
            ]
        
        donnees_revenus = self.get_revenus_filtres("Tout(e)s les Revenus", date_ref, periode)
        
        # Créer le PDF
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1
        )
        style_subtitle = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=13,
            spaceAfter=15,
            alignment=1
        )
        
        elements = []
        
        # Titre
        periode_affichage = self.formater_periode(periode, date_ref)
        titre = f"Rapport Comparatif 2 à 2 - {periode_affichage}"
        elements.append(Paragraph(titre, style_title))
        elements.append(Spacer(1, 20))
        
        # Traiter Dépenses Falaise
        depenses_falaise_groupees = {}
        for donnee in donnees_falaise:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in depenses_falaise_groupees:
                depenses_falaise_groupees[cle] = 0
            depenses_falaise_groupees[cle] += montant
        
        falaise_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(depenses_falaise_groupees.items()):
            if type_dep not in falaise_organisees:
                falaise_organisees[type_dep] = {}
            if source not in falaise_organisees[type_dep]:
                falaise_organisees[type_dep][source] = []
            falaise_organisees[type_dep][source].append((categorie_item, montant_total))
        
        # Traiter Dépenses Individus
        depenses_individus_groupees = {}
        for donnee in donnees_individus:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (categorie_item, source)
            if cle not in depenses_individus_groupees:
                depenses_individus_groupees[cle] = 0
            depenses_individus_groupees[cle] += montant
        
        individus_organisees = {}
        for (categorie_item, source), montant_total in sorted(depenses_individus_groupees.items()):
            if categorie_item not in individus_organisees:
                individus_organisees[categorie_item] = []
            individus_organisees[categorie_item].append((source, montant_total))
        
        # === TABLEAU DÉPENSES FALAISE ===
        elements.append(Paragraph(f"📤 DÉPENSES FALAISE ({filtre_falaise})", style_subtitle))
        elements.append(Spacer(1, 10))
        
        data_falaise = [["Type", "Catégorie", "Fournisseur", "Montant (TND)"]]
        table_styles_falaise = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        row_idx = 1
        total_falaise = 0
        
        for type_dep in sorted(falaise_organisees.keys()):
            start_type_row = row_idx
            nb_rows = 0
            
            for source in sorted(falaise_organisees[type_dep].keys()):
                start_source_row = row_idx
                categories = falaise_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    if i == 0 and row_idx == start_type_row:
                        data_falaise.append([type_dep, categorie_item, source, f"{montant_total:.2f}"])
                    elif i == 0:
                        data_falaise.append(["", categorie_item, source, f"{montant_total:.2f}"])
                    else:
                        data_falaise.append(["", categorie_item, "", f"{montant_total:.2f}"])
                    
                    total_falaise += montant_total
                    row_idx += 1
                    nb_rows += 1
                
                if len(categories) > 1:
                    table_styles_falaise.append(('SPAN', (2, start_source_row), (2, row_idx - 1)))
            
            if nb_rows > 1:
                table_styles_falaise.append(('SPAN', (0, start_type_row), (0, start_type_row + nb_rows - 1)))
        
        data_falaise.append(["TOTAL FALAISE:", "", "", f"{total_falaise:.2f}"])
        table_styles_falaise.append(('SPAN', (0, row_idx), (2, row_idx)))
        table_styles_falaise.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgrey))
        table_styles_falaise.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
        table_styles_falaise.append(('ALIGN', (0, row_idx), (2, row_idx), 'RIGHT'))
        
        table_falaise = Table(data_falaise, colWidths=[90, 110, 110, 90])
        table_falaise.setStyle(TableStyle(table_styles_falaise))
        elements.append(table_falaise)
        elements.append(Spacer(1, 30))
        
        # === TABLEAU DÉPENSES INDIVIDUS ===
        elements.append(Paragraph(f"👤 DÉPENSES INDIVIDUS ({filtre_individus})", style_subtitle))
        elements.append(Spacer(1, 10))
        
        data_individus = [["Catégorie", "Fournisseur", "Montant (TND)"]]
        table_styles_individus = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        row_idx = 1
        total_individus = 0
        
        for categorie_item in sorted(individus_organisees.keys()):
            start_row = row_idx
            sources_list = individus_organisees[categorie_item]
            
            for i, (source, montant_total) in enumerate(sources_list):
                if i == 0:
                    data_individus.append([categorie_item, source, f"{montant_total:.2f}"])
                else:
                    data_individus.append(["", source, f"{montant_total:.2f}"])
                
                total_individus += montant_total
                row_idx += 1
            
            if len(sources_list) > 1:
                table_styles_individus.append(('SPAN', (0, start_row), (0, row_idx - 1)))
        
        data_individus.append(["TOTAL INDIVIDUS:", "", f"{total_individus:.2f}"])
        table_styles_individus.append(('SPAN', (0, row_idx), (1, row_idx)))
        table_styles_individus.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgrey))
        table_styles_individus.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
        table_styles_individus.append(('ALIGN', (0, row_idx), (1, row_idx), 'RIGHT'))
        
        table_individus = Table(data_individus, colWidths=[150, 150, 100])
        table_individus.setStyle(TableStyle(table_styles_individus))
        elements.append(table_individus)
        elements.append(Spacer(1, 30))
        
        # === REVENUS (horizontal) ===
        elements.append(Paragraph("📥 REVENUS", style_subtitle))
        elements.append(Spacer(1, 10))
        
        revenus_par_date = {}
        for donnee in donnees_revenus:
            date_str, montant, source, categorie_item = donnee
            try:
                jour, mois, annee = date_str.split('/')
                date_key = f"{jour}/{mois}"
                date_obj = datetime(int(annee), int(mois), int(jour))
            except:
                date_key = date_str
                date_obj = datetime.now()
            
            if date_key not in revenus_par_date:
                revenus_par_date[date_key] = {'montant': 0, 'date_obj': date_obj}
            revenus_par_date[date_key]['montant'] += montant
        
        revenus_tries = sorted(revenus_par_date.items(), key=lambda x: x[1]['date_obj'])
        
        if revenus_tries:
            # Créer un tableau horizontal
            dates_rev = ["Date"] + [date_key for date_key, _ in revenus_tries]
            montants_rev = ["Montant"]
            total_revenus = 0
            for date_key, data_dict in revenus_tries:
                montants_rev.append(f"{data_dict['montant']:.2f}")
                total_revenus += data_dict['montant']
            
            data_rev = [dates_rev, montants_rev]
            
            # Calculer les largeurs de colonnes dynamiquement
            nb_cols = len(dates_rev)
            col_width = 400 / nb_cols if nb_cols > 0 else 50
            col_widths = [col_width] * nb_cols
            
            table_rev = Table(data_rev, colWidths=col_widths)
            table_rev.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, 1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table_rev)
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"TOTAL REVENUS: {total_revenus:.2f} TND", styles['Normal']))
        else:
            elements.append(Paragraph("Aucun revenu trouvé", styles['Normal']))
            total_revenus = 0
        
        elements.append(Spacer(1, 30))
        
        # === BILAN ===
        elements.append(Paragraph("💰 BILAN FINANCIER", style_subtitle))
        elements.append(Spacer(1, 10))
        
        total_depenses = total_falaise + total_individus
        benefice = total_revenus - total_depenses
        
        data_bilan = [
            ["Total Revenus:", f"{total_revenus:.2f} TND"],
            ["Total Dépenses Falaise:", f"{total_falaise:.2f} TND"],
            ["Total Dépenses Individus:", f"{total_individus:.2f} TND"],
            ["Total Dépenses:", f"{total_depenses:.2f} TND"],
        ]
        
        if benefice >= 0:
            data_bilan.append(["✅ BÉNÉFICE:", f"{benefice:.2f} TND"])
            color_bilan = colors.lightgreen
        else:
            data_bilan.append(["❌ PERTE:", f"{abs(benefice):.2f} TND"])
            color_bilan = colors.lightpink
        
        table_bilan = Table(data_bilan, colWidths=[250, 150])
        table_bilan.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 3), colors.beige),
            ('BACKGROUND', (0, 4), (-1, 4), color_bilan),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(table_bilan)
        
        # Générer le PDF
        doc.build(elements)
        messagebox.showinfo("Export réussi", f"Rapport PDF exporté : {filename}")

    def exporter_pdf_depenses(self, donnees, categorie, periode, date_ref):
        """Exporte uniquement les dépenses en PDF"""
        # Regrouper les données
        donnees_groupees = {}
        for donnee in donnees:
            date_str, montant, source, categorie_item, type_dep = donnee
            cle = (type_dep, categorie_item, source)
            if cle not in donnees_groupees:
                donnees_groupees[cle] = 0
            donnees_groupees[cle] += montant

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")],
            title=f"Exporter Dépenses - {categorie} - {self.formater_periode(periode, date_ref)}"
        )

        if not filename:
            return

        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1
        )
        style_normal = styles['Normal']

        elements = []

        # Titre
        titre = f"Rapport de Dépenses de {categorie} {self.formater_periode(periode, date_ref)}"
        elements.append(Paragraph(titre, style_title))

        # Période
        periode_affichage = self.formater_periode(periode, date_ref)
        elements.append(Paragraph(f"Période: {periode_affichage}", style_normal))
        elements.append(Spacer(1, 20))

        # Créer les données du tableau avec fusion
        data = [["Type Dépense", "Catégorie", "Fournisseur", "Montant Total (TND)"]]
        
        # Organiser les données pour la fusion
        donnees_organisees = {}
        for (type_dep, categorie_item, source), montant_total in sorted(donnees_groupees.items()):
            if type_dep not in donnees_organisees:
                donnees_organisees[type_dep] = {}
            if source not in donnees_organisees[type_dep]:
                donnees_organisees[type_dep][source] = []
            donnees_organisees[type_dep][source].append((categorie_item, montant_total))
        
        # Construire les données et les styles de fusion
        table_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        row_idx = 1
        total_general = 0
        
        for type_dep in sorted(donnees_organisees.keys()):
            start_type_row = row_idx
            nb_rows_for_type = 0
            
            for source in sorted(donnees_organisees[type_dep].keys()):
                start_source_row = row_idx
                categories = donnees_organisees[type_dep][source]
                
                for i, (categorie_item, montant_total) in enumerate(categories):
                    if i == 0 and row_idx == start_type_row:
                        data.append([type_dep, categorie_item, source, f"{montant_total:.2f}"])
                    elif i == 0:
                        data.append(["", categorie_item, source, f"{montant_total:.2f}"])
                    else:
                        data.append(["", categorie_item, "", f"{montant_total:.2f}"])
                    
                    total_general += montant_total
                    row_idx += 1
                    nb_rows_for_type += 1
                
                if len(categories) > 1:
                    table_styles.append(('SPAN', (2, start_source_row), (2, row_idx - 1)))
            
            if nb_rows_for_type > 1:
                table_styles.append(('SPAN', (0, start_type_row), (0, start_type_row + nb_rows_for_type - 1)))
        
        # Ajouter la ligne de total
        data.append(["TOTAL GÉNÉRAL:", "", "", f"{total_general:.2f}"])
        table_styles.append(('SPAN', (0, row_idx), (2, row_idx)))
        table_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgrey))
        table_styles.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
        table_styles.append(('ALIGN', (0, row_idx), (2, row_idx), 'RIGHT'))
        
        table = Table(data, colWidths=[100, 120, 120, 120])
        table.setStyle(TableStyle(table_styles))

        elements.append(table)
        doc.build(elements)
        messagebox.showinfo("Export réussi", f"Rapport PDF exporté : {filename}")

    def exporter_pdf_revenus(self, donnees, categorie, periode, date_ref):
        """Exporte uniquement les revenus en PDF avec format Date/Montant"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")],
            title=f"Exporter Revenus - {categorie} - {self.formater_periode(periode, date_ref)}"
        )

        if not filename:
            return

        # Regrouper par date
        donnees_par_date = {}
        for donnee in donnees:
            date_str, montant, source, categorie_item = donnee
            # Convertir DD/MM/YYYY en objet date pour tri
            try:
                jour, mois, annee = date_str.split('/')
                date_obj = datetime(int(annee), int(mois), int(jour))
                date_key = f"{jour}/{mois}"  # Format JJ/MM
            except:
                date_key = date_str
                date_obj = datetime.now()
            
            if date_key not in donnees_par_date:
                donnees_par_date[date_key] = {'montant': 0, 'date_obj': date_obj}
            donnees_par_date[date_key]['montant'] += montant
        
        # Trier par date
        donnees_triees = sorted(donnees_par_date.items(), key=lambda x: x[1]['date_obj'])

        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1
        )
        style_normal = styles['Normal']

        elements = []

        # Titre
        titre = f"Rapport de Revenus de {categorie} {self.formater_periode(periode, date_ref)}"
        elements.append(Paragraph(titre, style_title))

        # Période
        periode_affichage = self.formater_periode(periode, date_ref)
        elements.append(Paragraph(f"Période: {periode_affichage}", style_normal))
        elements.append(Spacer(1, 20))

        # Créer le tableau
        data = [["Date", "Montant (TND)"]]
        
        total_general = 0
        
        for date_key, data_dict in donnees_triees:
            montant = data_dict['montant']
            data.append([date_key, f"{montant:.2f}"])
            total_general += montant
        
        # Ajouter la ligne de total
        data.append(["TOTAL GÉNÉRAL:", f"{total_general:.2f}"])
        
        table_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle(table_styles))

        elements.append(table)
        doc.build(elements)
        messagebox.showinfo("Export réussi", f"Rapport PDF exporté : {filename}")