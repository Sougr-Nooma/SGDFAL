import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import Calendar
from datetime import datetime, timedelta
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import database
from database import get_all_depenses_by_compte, get_all_revenus_by_compte, get_categories_for_type
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

class Rapport:
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
            # Afficher la combobox catégorie avec une seule option
            self.combo_categorie.grid()
            try:
                self.combo_categorie.master.children['!label3'].grid()
            except:
                pass
            
            self.combo_categorie['values'] = ["REVENUS ET DÉPENSES"]
            self.categorie_var.set("REVENUS ET DÉPENSES")
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

        if type_val != "TOUT" and not categorie:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une catégorie.")
            return

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
        """Affiche le rapport des revenus uniquement"""
        titre = f"Rapport de Revenus de {categorie} {self.formater_periode(periode, date_ref)}"
        self.resultat_text.insert(tk.END, titre + "\n\n")
        
        if not donnees:
            self.resultat_text.insert(tk.END, "Aucune donnée trouvée pour cette période.\n")
            return
        
        # Afficher avec la logique existante
        donnees_groupees = {}
        for donnee in donnees:
            date_str, montant, source, categorie_item = donnee
            cle = (categorie_item, source)
            if cle not in donnees_groupees:
                donnees_groupees[cle] = 0
            donnees_groupees[cle] += montant
        
        periode_affichage = self.formater_periode(periode, date_ref)
        self.resultat_text.insert(tk.END, f"Période: {periode_affichage}\n\n")
        
        header = f"{'Catégorie':<30} {'Source':<30} {'Montant Total (TND)':<20}\n"
        separator = "-" * 82 + "\n"
        self.resultat_text.insert(tk.END, header)
        self.resultat_text.insert(tk.END, separator)
        
        donnees_organisees = {}
        for (categorie_item, source), montant_total in sorted(donnees_groupees.items()):
            if categorie_item not in donnees_organisees:
                donnees_organisees[categorie_item] = []
            donnees_organisees[categorie_item].append((source, montant_total))
        
        total_general = 0
        for categorie_item in sorted(donnees_organisees.keys()):
            cat_printed = False
            for source, montant_total in donnees_organisees[categorie_item]:
                cat_str = categorie_item if not cat_printed else ""
                
                ligne = f"{cat_str:<30} {source:<30} {montant_total:<20.2f}\n"
                self.resultat_text.insert(tk.END, ligne)
                total_general += montant_total
                
                if not cat_printed:
                    cat_printed = True
        
        self.resultat_text.insert(tk.END, separator)
        self.resultat_text.insert(tk.END, f"\n{'TOTAL GÉNÉRAL:':<62} {total_general:<20.2f} TND\n")

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

        query += " ORDER BY date ASC"
        
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
            
            result.append((formatted_date, montant, source, categorie_item, date_str))
        
        return result

    def exporter_excel(self):
        """Exporte le rapport en Excel (.xlsx) avec mise en forme"""
        type_val = self.type_var.get()
        categorie = self.categorie_var.get()
        periode = self.periode_selectionnee
        date_ref = self.date_selectionnee

        if not categorie:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une catégorie.")
            return

        if type_val == "Dépenses":
            type_depense = self.type_depense_var.get()
            donnees = self.get_depenses_filtrees(categorie, date_ref, periode, type_depense)
        else:
            donnees = self.get_revenus_filtres(categorie, date_ref, periode)

        if not donnees:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
            return

        # Regrouper les données
        donnees_groupees = {}
        for donnee in donnees:
            if type_val == "Dépenses":
                date_str, montant, source, categorie_item, type_dep = donnee
                cle = (type_dep, categorie_item, source)
            else:
                date_str, montant, source, categorie_item = donnee
                cle = (categorie_item, source)
            
            if cle not in donnees_groupees:
                donnees_groupees[cle] = 0
            donnees_groupees[cle] += montant

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Fichiers Excel", "*.xlsx"), ("Tous les fichiers", "*.*")],
            title=f"Exporter {type_val} - {categorie} - {self.formater_periode(periode, date_ref)}"
        )

        if not filename:
            return

        # Créer le workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Rapport"

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
        right_align = Alignment(horizontal='right', vertical='center')

        # Titre
        titre = f"Rapport de {type_val} de {categorie} {self.formater_periode(periode, date_ref)}"
        ws.merge_cells('A1:D1')
        cell = ws['A1']
        cell.value = titre
        cell.font = titre_font
        cell.alignment = center_align

        # Période
        periode_affichage = self.formater_periode(periode, date_ref)
        ws.merge_cells('A3:D3')
        cell = ws['A3']
        cell.value = f"Période: {periode_affichage}"
        cell.alignment = center_align

        # En-tête du tableau
        row_idx = 5
        
        if type_val == "Dépenses":
            headers = ["Type Dépense", "Catégorie", "Fournisseur", "Montant Total (TND)"]
            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
                cell.alignment = center_align
            
            # Organiser les données
            donnees_organisees = {}
            for (type_dep, categorie_item, source), montant_total in sorted(donnees_groupees.items()):
                if type_dep not in donnees_organisees:
                    donnees_organisees[type_dep] = {}
                if source not in donnees_organisees[type_dep]:
                    donnees_organisees[type_dep][source] = []
                donnees_organisees[type_dep][source].append((categorie_item, montant_total))
            
            # Écrire les données
            row_idx += 1
            total_general = 0
            
            for type_dep in sorted(donnees_organisees.keys()):
                start_type_row = row_idx
                
                for source in sorted(donnees_organisees[type_dep].keys()):
                    start_source_row = row_idx
                    categories = donnees_organisees[type_dep][source]
                    
                    for i, (categorie_item, montant_total) in enumerate(categories):
                        # Type Dépense
                        cell = ws.cell(row=row_idx, column=1)
                        if i == 0 and row_idx == start_type_row:
                            cell.value = type_dep
                        cell.fill = data_fill
                        cell.border = border
                        cell.alignment = center_align
                        
                        # Catégorie
                        cell = ws.cell(row=row_idx, column=2)
                        cell.value = categorie_item
                        cell.fill = data_fill
                        cell.border = border
                        cell.alignment = center_align
                        
                        # Fournisseur
                        cell = ws.cell(row=row_idx, column=3)
                        if i == 0:
                            cell.value = source
                        cell.fill = data_fill
                        cell.border = border
                        cell.alignment = center_align
                        
                        # Montant
                        cell = ws.cell(row=row_idx, column=4)
                        cell.value = montant_total
                        cell.number_format = '0.00'
                        cell.fill = data_fill
                        cell.border = border
                        cell.alignment = center_align
                        
                        total_general += montant_total
                        row_idx += 1
                    
                    # Fusionner les cellules du fournisseur
                    if len(categories) > 1:
                        ws.merge_cells(start_row=start_source_row, start_column=3, 
                                      end_row=row_idx-1, end_column=3)
                
                # Fusionner les cellules du type de dépense
                if row_idx - start_type_row > 1:
                    ws.merge_cells(start_row=start_type_row, start_column=1, 
                                  end_row=row_idx-1, end_column=1)
            
            # Total général
            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=3)
            cell = ws.cell(row=row_idx, column=1)
            cell.value = "TOTAL GÉNÉRAL:"
            cell.font = total_font
            cell.fill = total_fill
            cell.border = border
            cell.alignment = right_align
            
            cell = ws.cell(row=row_idx, column=4)
            cell.value = total_general
            cell.number_format = '0.00'
            cell.font = total_font
            cell.fill = total_fill
            cell.border = border
            cell.alignment = center_align
            
        else:
            # Pour les revenus
            headers = ["Catégorie", "Source", "Montant Total (TND)"]
            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
                cell.alignment = center_align
            
            # Organiser les données
            donnees_organisees = {}
            for (categorie_item, source), montant_total in sorted(donnees_groupees.items()):
                if categorie_item not in donnees_organisees:
                    donnees_organisees[categorie_item] = []
                donnees_organisees[categorie_item].append((source, montant_total))
            
            # Écrire les données
            row_idx += 1
            total_general = 0
            
            for categorie_item in sorted(donnees_organisees.keys()):
                start_row = row_idx
                sources_list = donnees_organisees[categorie_item]
                
                for i, (source, montant_total) in enumerate(sources_list):
                    # Catégorie
                    cell = ws.cell(row=row_idx, column=1)
                    if i == 0:
                        cell.value = categorie_item
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    # Source
                    cell = ws.cell(row=row_idx, column=2)
                    cell.value = source
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    # Montant
                    cell = ws.cell(row=row_idx, column=3)
                    cell.value = montant_total
                    cell.number_format = '0.00'
                    cell.fill = data_fill
                    cell.border = border
                    cell.alignment = center_align
                    
                    total_general += montant_total
                    row_idx += 1
                
                # Fusionner les cellules de catégorie
                if len(sources_list) > 1:
                    ws.merge_cells(start_row=start_row, start_column=1, 
                                  end_row=row_idx-1, end_column=1)
            
            # Total général
            ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=2)
            cell = ws.cell(row=row_idx, column=1)
            cell.value = "TOTAL GÉNÉRAL:"
            cell.font = total_font
            cell.fill = total_fill
            cell.border = border
            cell.alignment = right_align
            
            cell = ws.cell(row=row_idx, column=3)
            cell.value = total_general
            cell.number_format = '0.00'
            cell.font = total_font
            cell.fill = total_fill
            cell.border = border
            cell.alignment = center_align

        # Ajuster la largeur des colonnes
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 25
        ws.column_dimensions['D'].width = 20

        # Sauvegarder le fichier
        wb.save(filename)
        messagebox.showinfo("Export réussi", f"Fichier Excel exporté : {filename}")

    def exporter_pdf(self):
        """Exporte le rapport en PDF"""
        type_val = self.type_var.get()
        categorie = self.categorie_var.get()
        periode = self.periode_selectionnee
        date_ref = self.date_selectionnee

        if not categorie:
            messagebox.showwarning("Erreur", "Veuillez sélectionner une catégorie.")
            return

        if type_val == "Dépenses":
            type_depense = self.type_depense_var.get()
            donnees = self.get_depenses_filtrees(categorie, date_ref, periode, type_depense)
        else:
            donnees = self.get_revenus_filtres(categorie, date_ref, periode)

        if not donnees:
            messagebox.showwarning("Avertissement", "Aucune donnée à exporter.")
            return

        # Regrouper les données
        donnees_groupees = {}
        for donnee in donnees:
            if type_val == "Dépenses":
                date_str, montant, source, categorie_item, type_dep = donnee
                cle = (type_dep, categorie_item, source)
            else:
                date_str, montant, source, categorie_item = donnee
                cle = (categorie_item, source)
            
            if cle not in donnees_groupees:
                donnees_groupees[cle] = 0
            donnees_groupees[cle] += montant

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")],
            title=f"Exporter {type_val} - {categorie} - {self.formater_periode(periode, date_ref)}"
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
        titre = f"Rapport de {type_val} de {categorie} {self.formater_periode(periode, date_ref)}"
        elements.append(Paragraph(titre, style_title))

        # Période
        periode_affichage = self.formater_periode(periode, date_ref)
        elements.append(Paragraph(f"Période: {periode_affichage}", style_normal))
        elements.append(Spacer(1, 20))

        # Créer les données du tableau avec fusion
        if type_val == "Dépenses":
            data = [["Type Dépense", "Catégorie", "Fournisseur", "Montant Total (TND)"]]
            
            # Organiser les données pour la fusion par Type -> Fournisseur -> Catégories
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
                        # Mettre le type et source uniquement sur la première ligne
                        if i == 0 and row_idx == start_type_row:
                            data.append([type_dep, categorie_item, source, f"{montant_total:.2f}"])
                        elif i == 0:
                            data.append(["", categorie_item, source, f"{montant_total:.2f}"])
                        else:
                            data.append(["", categorie_item, "", f"{montant_total:.2f}"])
                        
                        total_general += montant_total
                        row_idx += 1
                        nb_rows_for_type += 1
                    
                    # Fusionner les cellules du fournisseur si plusieurs catégories
                    if len(categories) > 1:
                        table_styles.append(('SPAN', (2, start_source_row), (2, row_idx - 1)))
                
                # Fusionner les cellules du type de dépense pour toutes ses lignes
                if nb_rows_for_type > 1:
                    table_styles.append(('SPAN', (0, start_type_row), (0, start_type_row + nb_rows_for_type - 1)))
            
            # Ajouter la ligne de total
            data.append(["TOTAL GÉNÉRAL:", "", "", f"{total_general:.2f}"])
            table_styles.append(('SPAN', (0, row_idx), (2, row_idx)))
            table_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgrey))
            table_styles.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
            table_styles.append(('ALIGN', (0, row_idx), (2, row_idx), 'RIGHT'))
            
            col_widths = [100, 120, 120, 120]
            
        else:
            # Pour les revenus
            data = [["Catégorie", "Source", "Montant Total (TND)"]]
            
            donnees_organisees = {}
            for (categorie_item, source), montant_total in sorted(donnees_groupees.items()):
                if categorie_item not in donnees_organisees:
                    donnees_organisees[categorie_item] = []
                donnees_organisees[categorie_item].append((source, montant_total))
            
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
            
            for categorie_item in sorted(donnees_organisees.keys()):
                start_row = row_idx
                sources_list = donnees_organisees[categorie_item]
                
                for i, (source, montant_total) in enumerate(sources_list):
                    if i == 0:
                        data.append([categorie_item, source, f"{montant_total:.2f}"])
                    else:
                        data.append(["", source, f"{montant_total:.2f}"])
                    
                    total_general += montant_total
                    row_idx += 1
                
                # Fusionner les cellules de catégorie si plusieurs sources
                if len(sources_list) > 1:
                    table_styles.append(('SPAN', (0, start_row), (0, row_idx - 1)))
            
            # Ajouter la ligne de total
            data.append(["", "TOTAL GÉNÉRAL:", f"{total_general:.2f}"])
            table_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightgrey))
            table_styles.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))
            
            col_widths = [160, 160, 120]

        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle(table_styles))

        elements.append(table)
        doc.build(elements)
        messagebox.showinfo("Export réussi", f"Rapport PDF exporté : {filename}")