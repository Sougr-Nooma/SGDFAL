from responsive_accueil import ResponsiveAccueil
import tkinter as tk
from tkinter import ttk, messagebox
import database
from depenses import Depenses
from revenus import Revenus
from rapport import Rapport
from responsive_manager import ResponsiveManager

class ResponsiveApp:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        
        # Initialisation de la base de données; aucun compte n'est actif avant authentification.
        database.init_db()
        self.compte_actif = None
        self.langue = "FR"
        
        # Configuration responsive de la fenêtre principale
        ResponsiveManager.configure_grid(root, [0, 1], [1])
        
        root.withdraw()
        self.setup_responsive_navigation()
        self.setup_responsive_content()
        
        # Bind des événements de redimensionnement
        root.bind("<Configure>", self.on_window_resize)
        self._ouvrir_authentification()
        
    def _ouvrir_authentification(self):
        """Exige une authentification ou la création du premier compte."""
        comptes = database.get_all_comptes()
        fenetre = tk.Toplevel(self.root)
        fenetre.title("Connexion - SGD")
        fenetre.geometry("360x330" if comptes else "360x390")
        fenetre.resizable(False, False)
        # La racine est masquée jusqu'à l'authentification; une fenêtre
        # transitoire serait également cachée avec elle sous Windows.
        fenetre.grab_set()
        fenetre.protocol("WM_DELETE_WINDOW", self.root.destroy)

        mode_creation = not comptes
        tk.Label(
            fenetre,
            text=("Créer le premier compte" if mode_creation else "Connexion"),
            font=("Arial", 14, "bold"),
        ).pack(pady=12)

        form = tk.Frame(fenetre)
        form.pack(fill="x", padx=24)
        tk.Label(form, text="Nom du compte").pack(anchor="w")
        if comptes:
            compte_var = tk.StringVar(value=comptes[0])
            compte_widget = ttk.Combobox(form, textvariable=compte_var, values=comptes, state="readonly")
        else:
            compte_var = tk.StringVar()
            compte_widget = ttk.Entry(form, textvariable=compte_var)
        compte_widget.pack(fill="x", pady=(0, 8))

        email_var = tk.StringVar()
        if mode_creation:
            tk.Label(form, text="Adresse e-mail").pack(anchor="w")
            ttk.Entry(form, textvariable=email_var).pack(fill="x", pady=(0, 8))

        tk.Label(form, text="Mot de passe" + (" (8 caractères minimum)" if mode_creation else "")).pack(anchor="w")
        password_entry = ttk.Entry(form, show="*")
        password_entry.pack(fill="x", pady=(0, 10))

        def submit():
            name = compte_var.get().strip()
            password = password_entry.get()
            if mode_creation:
                email = email_var.get().strip()
                if not name or "@" not in email or len(password) < 8:
                    messagebox.showwarning(
                        "Informations invalides",
                        "Entrez un nom, une adresse e-mail valide et un mot de passe d'au moins 8 caractères.",
                        parent=fenetre,
                    )
                    return
                success = database.ajouter_compte(name, email, password)
            else:
                success = database.verifier_connexion(name, password)

            if not success:
                messagebox.showerror(
                    "Connexion refusée" if not mode_creation else "Création impossible",
                    "Mot de passe incorrect." if not mode_creation else "Ce nom de compte ou cette adresse e-mail existe déjà.",
                    parent=fenetre,
                )
                return

            self.compte_actif = name
            fenetre.destroy()
            self.root.deiconify()
            self.show_frame("accueil")

        ttk.Button(
            fenetre,
            text=("Créer le compte" if mode_creation else "Se connecter"),
            command=submit,
        ).pack(fill="x", padx=24, pady=8)
        password_entry.bind("<Return>", lambda _event: submit())
        password_entry.focus_set()

    def setup_window(self):
        """Configure la fenêtre principale responsive"""
        self.root.title("SGD - Gestion Restaurant Responsive")
        
        # Adapter la taille à l'écran
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if screen_width < 1366:
            self.root.geometry("1000x650")
        else:
            self.root.geometry("1200x750")
            
        self.root.minsize(900, 600)  # Taille minimale

    def setup_responsive_navigation(self):
        """Crée la navigation responsive"""
        nav_frame = tk.Frame(self.root, bg="#2c3e50")
        nav_frame.grid(row=0, column=0, sticky="ew")
        
        # Configuration grid responsive pour la navigation
        ResponsiveManager.configure_grid(nav_frame, [1], [0, 1, 0])
        
        # Logo à gauche
        logo_frame = tk.Frame(nav_frame, bg="#2c3e50")
        logo_frame.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        tk.Label(logo_frame, text="SGD", font=("Arial", 16, "bold"), 
                fg="white", bg="#2c3e50").pack()
        
        # Boutons de navigation centrés
        nav_buttons_frame = tk.Frame(nav_frame, bg="#2c3e50")
        nav_buttons_frame.grid(row=0, column=1, sticky="ew", padx=20)
        
        # Configuration grid pour les boutons de navigation
        buttons = ["Accueil", "Revenus", "Dépenses", "Rapport"]
        for i, text in enumerate(buttons):
            nav_buttons_frame.grid_columnconfigure(i, weight=1)
            btn = tk.Button(
                nav_buttons_frame, text=text, font=("Arial", 11),
                bg="#34495e", fg="white", relief="flat", padx=12, pady=8,
                command=lambda p=text.lower(): self.show_frame(p)
            )
            btn.grid(row=0, column=i, sticky="ew", padx=2)
        
        # Bouton paramètres à droite
        settings_btn = tk.Button(
            nav_frame, text="⚙️", font=("Arial", 14),
            bg="#34495e", fg="white", relief="flat", padx=10,
            command=self.ouvrir_fenetre_parametres
        )
        settings_btn.grid(row=0, column=2, padx=15, pady=10, sticky="e")

    def setup_responsive_content(self):
        """Configure la zone de contenu responsive"""
        self.container = tk.Frame(self.root, bg="white")
        self.container.grid(row=1, column=0, sticky="nsew")
        
        # Configuration grid pour le container
        ResponsiveManager.configure_grid(self.container, [1], [1])
        
        self.frames = {}
        for page_name in ["accueil", "revenus", "depenses", "rapport"]:
            frame = tk.Frame(self.container, bg="white")
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[page_name] = frame
            
            # Configuration grid pour chaque frame
            ResponsiveManager.configure_grid(frame, [1], [1])
        
        self.show_frame("accueil")

    def on_window_resize(self, event):
        """Gère le redimensionnement de la fenêtre"""
        if event.widget == self.root:
            width = event.width
            # Mettre à jour les tailles de police dans les modules
            if hasattr(self, 'accueil_module'):
                self.accueil_module.update_font_sizes(width)

    def show_frame(self, page_name):
        """Affiche la frame demandée"""
        frame = self.frames[page_name]
        frame.tkraise()

        # Mettre à jour les tailles de police
        width = self.root.winfo_width()
        
        if page_name == "accueil":
            if not hasattr(self, 'accueil_module'):
                self.accueil_module = ResponsiveAccueil(frame, self.compte_actif)
            else:
                self.accueil_module.compte_actif = self.compte_actif
            self.accueil_module.update_font_sizes(width)
            self.accueil_module.afficher()
        
        elif page_name == "depenses":
            if not hasattr(self, 'depenses_module'):
                self.depenses_module = Depenses(frame, self.compte_actif)
            else:
                self.depenses_module.compte_actif = self.compte_actif
            self.depenses_module.afficher()
            
        elif page_name == "revenus":
            if not hasattr(self, 'revenus_module'):
                self.revenus_module = Revenus(frame, self.compte_actif)
            else:
                self.revenus_module.compte_actif = self.compte_actif
            self.revenus_module.afficher()
            
        elif page_name == "rapport":
            if not hasattr(self, 'rapport_module'):
                self.rapport_module = Rapport(frame, self.compte_actif)
            else:
                self.rapport_module.compte_actif = self.compte_actif
            self.rapport_module.afficher()

    def ouvrir_fenetre_parametres(self):
        """Ouvre la fenêtre des paramètres (version simplifiée pour l'exemple)"""
        messagebox.showinfo("Paramètres", "Fonctionnalité paramètres")

if __name__ == "__main__":
    root = tk.Tk()
    app = ResponsiveApp(root)
    root.mainloop()