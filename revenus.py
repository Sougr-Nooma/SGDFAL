import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
import database
from database import get_all_revenus_by_compte, ajouter_revenu
from ui_utils import configurer_icone_fenetre, placer_fenetre_sous_navbar
from datetime import datetime
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class Revenus:
    def __init__(self, parent_frame, compte_actif):
        self.parent_frame = parent_frame
        self.compte_actif = compte_actif

    def afficher(self):
        """Affiche la page Revenus avec tableau, bouton et graphique dans un scroll"""
        # Effacer tout contenu existant
        for widget in self.parent_frame.winfo_children():
            widget.destroy()

        # === Créer un Canvas + Frame scrollable ===
        scroll_canvas = tk.Canvas(self.parent_frame, bg="white")
        scrollbar = ttk.Scrollbar(self.parent_frame, orient="vertical", command=scroll_canvas.yview)
        main_frame = tk.Frame(scroll_canvas, bg="white")

        main_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        canvas_window = scroll_canvas.create_window((0, 0), window=main_frame, anchor="nw")  # Ancrage en haut à gauche
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        # Gestion du défilement avec la molette
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
            text="💰 Gestion des Revenus",
            font=("Arial", 18, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(side="left", padx=10)
        btn_ajouter = tk.Button(
            top_frame,
            text="➕ Ajouter un revenu",
            bg="#2ecc71",
            fg="white",
            font=("Arial", 12),
            command=self.ouvrir_formulaire_ajout
        )
        btn_ajouter.pack(side="right", padx=10)

        # === Tableau des 7 derniers revenus ===
        tk.Label(
            content_container,
            text="📋 Les 7 derniers revenus",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(pady=(20, 10), anchor="center")

        table_container = tk.Frame(content_container, bg="white")
        table_container.pack(fill="x", pady=10, padx=50)

        columns = ("Date", "Montant", "Source", "Description")
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", height=7)
        for col in columns:
            self.tree.heading(col, text=col, anchor="center")
            if col == "Date":
                self.tree.column(col, width=100, anchor="center")
            elif col == "Montant":
                self.tree.column(col, width=90, anchor="center")
            elif col == "Source":
                self.tree.column(col, width=140, anchor="center")
            else:
                self.tree.column(col, width=200, anchor="center")

        self.tree.pack(side="left", fill="x", expand=True)
        tree_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=tree_scrollbar.set)
        tree_scrollbar.pack(side="right", fill="y")

        self.charger_revenus()

        # === Graphique en barres : revenus des 3 derniers mois ===
        tk.Label(
            content_container,
            text="📊 Statistiques des Revenus",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#2c3e50"
        ).pack(pady=(30, 20), anchor="center")

        # Récupérer les données
        revenus_par_mois = self.get_revenus_3_derniers_mois()
        if revenus_par_mois:
            # Inverser l'ordre pour avoir : [Janvier, Février, Mars] → du plus ancien au plus récent
            revenus_par_mois.reverse()
            mois_labels = [item[0] for item in revenus_par_mois]
            montants = [item[1] for item in revenus_par_mois]

            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(mois_labels, montants, color=["#95a5a6", "#3498db", "#2ecc71"])
            ax.set_title("Revenus des 3 derniers mois", fontsize=12, pad=15)
            ax.set_ylabel("Montant (TND)")
            ax.yaxis.grid(True, linestyle='--', alpha=0.6)

            
            # === Afficher les montants AU DESSUS du graphique, à une hauteur fixe ===
            # Récupérer la limite supérieure du graphique
            y_max = max(ax.get_ylim()[1], 1.0)
            # Position Y fixe : y_max + 2% de l'amplitude totale du graphique
            y_text = y_max + (y_max - ax.get_ylim()[0]) * 0.001

            for bar, montant in zip(bars, montants):
                x_pos = bar.get_x() + bar.get_width() / 2
                # Texte au-dessus de la barre, à hauteur fixe
                ax.text(
                    x_pos,
                    y_text,
                    f"{montant:.2f} TND",
                    ha='center',
                    va='bottom',  # Toujours ancré en bas du texte → reste au-dessus
                    fontweight='bold',
                    fontsize=10,
                    color='black',
                    bbox=dict(
                        boxstyle="round,pad=0.2",
                        facecolor='lightblue',
                        edgecolor='darkblue',
                        alpha=0.8
                    ),
                    zorder=10  # Pour être au-dessus des barres
                )

            # Ajuster les limites Y pour laisser de la place aux textes
            ax.set_ylim(0, y_max * 1.1)  # Ajoute 10% d'espace en haut
            
            graph_container = tk.Frame(content_container, bg="white")
            graph_container.pack(fill="x", expand=True, pady=20, padx=20)
            canvas = FigureCanvasTkAgg(fig, master=graph_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            plt.close(fig)

            # === Comparaison des paires consécutives ===
            messages = []
            for i in range(len(montants) - 1):
                mois1_label = mois_labels[i]
                mois2_label = mois_labels[i+1]
                mois1_montant = montants[i]
                mois2_montant = montants[i+1]

                if mois1_montant > mois2_montant:
                    somme = mois1_montant + mois2_montant
                    diff = mois2_montant - mois1_montant
                    message = (
                        f"⚠️ Attention ! Les revenus de {mois1_label} ({mois1_montant:.2f} TND) "
                        f"sont supérieurs à ceux de {mois2_label} ({mois2_montant:.2f} TND).\n"
                        f"Somme cumulée : {somme:.2f} TND | Différence : {diff:.2f} TND"
                    )
                    messages.append(message)

            # Afficher tous les messages
            for msg in messages:
                tk.Label(
                    content_container,
                    text=msg,
                    font=("Arial", 11, "bold"),
                    bg="white",
                    fg="#e74c3c",
                    justify="center",
                    wraplength=600
                ).pack(pady=(0, 10))

            if not messages:
                tk.Label(
                    content_container,
                    text="✅ Tous les mois récents ont des revenus stables ou en hausse.",
                    font=("Arial", 11, "italic"),
                    bg="white",
                    fg="#27ae60",
                    justify="center"
                ).pack(pady=(0, 10))

        else:
            tk.Label(content_container, text="Aucun revenu enregistré.", font=("Arial", 12), bg="white", fg="#666").pack(pady=20)

        # Mise à jour du canvas pour centrer le contenu
        def update_canvas_width(event):
            scroll_canvas.itemconfigure(canvas_window, width=event.width)
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        scroll_canvas.bind("<Configure>", update_canvas_width)
        
    def charger_revenus(self):
        """Charge tous les revenus du compte actif dans le tableau"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        revenus = get_all_revenus_by_compte(self.compte_actif)[:7]
        for rev in revenus:
            sql_date = rev[0]
            try:
                date_obj = datetime.strptime(sql_date, "%Y-%m-%d")
                display_date = date_obj.strftime("%d/%m/%Y")  # ✅ Formattage correct
            except Exception:
                display_date = "Date invalide"
            self.tree.insert("", "end", values=(
                display_date,  # date
                f"{rev[1]:.2f} TND",  # montant
                rev[2] or "-",  # source
                rev[3] or "-"   # description
            ))


    def get_revenus_3_derniers_mois(self):
        """Renvoie les revenus agrégés des 3 derniers mois complets, triés du plus ancien au plus récent."""
        from datetime import datetime

        conn = database.connect_db()
        cursor = conn.cursor()

        # Obtenir la date du jour
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # Générer les 3 derniers mois au format 'YYYY-MM'
        mois_cles = []
        for i in range(3):
            year = current_year
            month = current_month - i
            while month <= 0:
                month += 12
                year -= 1
            mois_cles.append(f"{year}-{month:02d}")

        # Requête SQL : somme par mois
        mois_placeholders = ','.join(['?'] * len(mois_cles))
        query = f"""
            SELECT strftime('%Y-%m', date) AS mois, SUM(montant)
            FROM revenus
            WHERE compte = ? AND strftime('%Y-%m', date) IN ({mois_placeholders})
            GROUP BY mois
            ORDER BY mois ASC 
        """
        cursor.execute(query, (self.compte_actif,) + tuple(mois_cles))
        resultats = cursor.fetchall()
        conn.close()

        # Formater les mois en "Mois AAAA" (ex: "Jan 2025")
        mois_noms = {
            "01": "Jan", "02": "Fév", "03": "Mar", "04": "Avr",
            "05": "Mai", "06": "Juin", "07": "Juil", "08": "Août",
            "09": "Sep", "10": "Oct", "11": "Nov", "12": "Déc"
        }

        # Créer un dict pour garantir l'ordre même si un mois n’a pas de données
        revenus_dict = {mois: 0.0 for mois in mois_cles}
        for mois_sql, total in resultats:
            if mois_sql in revenus_dict:
                revenus_dict[mois_sql] = total or 0.0

        # Convertir en liste triée (du plus ancien au plus récent)
        liste_finale = []
        for mois_sql in mois_cles:
            annee, num_mois = mois_sql.split('-')
            nom_mois = mois_noms.get(num_mois, num_mois)
            affichage = f"{nom_mois} {annee}"
            liste_finale.append((affichage, revenus_dict[mois_sql]))

        return liste_finale
    
    def ouvrir_formulaire_ajout(self):
        """Ouvre une fenêtre pour ajouter un revenu avec calendrier"""
        ajout_fenetre = tk.Toplevel(self.parent_frame)
        ajout_fenetre.title("Ajouter un revenu")
        configurer_icone_fenetre(ajout_fenetre, "revenus")
        ajout_fenetre.geometry("400x450")
        placer_fenetre_sous_navbar(ajout_fenetre, self.parent_frame, 400, 450)
        ajout_fenetre.resizable(False, False)
        ajout_fenetre.transient(self.parent_frame)
        ajout_fenetre.grab_set()
        ajout_fenetre.configure(bg="#f0f0f0")

        frame_central = tk.Frame(ajout_fenetre, bg="#f0f0f0")
        frame_central.pack(expand=True, padx=20, pady=20)

        # --- Date (avec calendrier) ---
        tk.Label(frame_central, text="Date :", bg="#f0f0f0").pack(pady=5)

        btn_date = tk.Button(
            frame_central,
            text="Cliquez pour choisir la date",
            command=lambda: self.ouvrir_calendrier(btn_date),
            bg="white",
            fg="black",
            font=("Arial", 10),
            padx=10,
            pady=8,
            width=20,
            borderwidth=1,
            relief="solid"
        )
        btn_date.pack(pady=5, padx=20, fill="x")

        today = datetime.now().strftime("%d/%m/%Y")
        btn_date.config(text=today)

        # --- Montant ---
        tk.Label(frame_central, text="Montant (TND) :", bg="#f0f0f0").pack(pady=5)
        montant_var = tk.DoubleVar(value=0.0)
        spinbox_montant = tk.Spinbox(
            frame_central,
            textvariable=montant_var,
            from_=0.01,
            to=99999.99,
            increment=0.01,
            width=15,
            font=("Arial", 12),
            justify="right"
        )
        spinbox_montant.pack(pady=5, padx=20, fill="x")

        # --- Source ---
        tk.Label(frame_central, text="Source :", bg="#f0f0f0").pack(pady=5)
        source_var = tk.StringVar(value="RECETTE")
        combo_source = ttk.Combobox(
            frame_central,
            textvariable=source_var,
            values=["RECETTE", "LOCATION", "AUTRE"],
            state="readonly",
            font=("Arial", 12)
        )
        combo_source.pack(pady=5, padx=20, fill="x")

        # --- Description (optionnel) ---
        tk.Label(frame_central, text="Description (optionnel) :", bg="#f0f0f0").pack(pady=5)
        text_description = tk.Text(frame_central, font=("Arial", 12), height=3, width=30, relief="solid", bd=1)
        text_description.pack(pady=5, padx=20, fill="x")

        def ajouter():
            # Récupérer la date du bouton
            date_str = btn_date.cget("text")
            if date_str == "Cliquez pour choisir la date":
                messagebox.showwarning("Erreur", "Veuillez sélectionner une date.")
                return

            try:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning("Erreur", "Format de date invalide. Utilisez jj/mm/aaaa.")
                return

            try:
                montant = montant_var.get()
            except (ValueError, tk.TclError):
                messagebox.showwarning("Erreur", "Veuillez saisir un montant valide.")
                return
            source = source_var.get()
            description = text_description.get("1.0", "end-1c").strip()

            if not math.isfinite(montant) or montant <= 0:
                messagebox.showwarning("Erreur", "Le montant doit être un nombre valide supérieur à 0.")
                return
            if not source:
                messagebox.showwarning("Erreur", "La source est obligatoire.")
                return

            # Convertir la date validée au format SQL : AAAA-MM-JJ
            sql_date = date_obj.strftime("%Y-%m-%d")

            if ajouter_revenu(sql_date, montant, source, description, self.compte_actif):
                messagebox.showinfo("Succès", "Revenu ajouté avec succès.")

                # Réinitialiser les champs
                montant_var.set(0.0)
                source_var.set("AUTRE")
                text_description.delete("1.0", "end")
                btn_date.config(text="Cliquez pour choisir la date")

                ajout_fenetre.destroy()  # Fermer la fenêtre
                self.afficher()  # Rafraîchir la liste et les statistiques
            else:
                messagebox.showerror("Erreur", "Échec de l'ajout.")

        btn_valider = tk.Button(
            frame_central,
            text="✅ Valider le revenu",
            bg="#2ecc71",
            fg="white",
            command=ajouter
        )
        btn_valider.pack(pady=15, padx=20, fill="x")

        btn_annuler = tk.Button(
            frame_central,
            text="❌ Annuler",
            bg="#e74c3c",
            fg="white",
            command=ajout_fenetre.destroy
        )
        btn_annuler.pack(pady=5, padx=20, fill="x")

    def ouvrir_calendrier(self, btn_date):
        """Ouvre le calendrier et met à jour le bouton avec la date choisie"""
        cal_window = tk.Toplevel(self.parent_frame.winfo_toplevel())
        cal_window.title("Choisir la date")
        configurer_icone_fenetre(cal_window, "revenus")
        cal_window.geometry("400x500")
        cal_window.configure(bg="white")
        cal_window.transient(self.parent_frame.winfo_toplevel())
        cal_window.grab_set()
        cal_window.focus_force()

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

        def on_date_selected(event):
            try:
                selected_date = cal.selection_get()
                btn_date.config(text=selected_date.strftime("%d/%m/%Y"))
                cal_window.destroy()
            except (AttributeError, TypeError, ValueError):
                messagebox.showerror("Erreur", "Impossible de lire la date sélectionnée.")

        cal.bind("<<CalendarSelected>>", on_date_selected)