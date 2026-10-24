import sqlite3
import csv
import hashlib
import hmac
import os
import secrets
import sys
import time
from contextlib import closing
from pathlib import Path
from tkinter import messagebox

_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 310_000
_sqlite_connect = sqlite3.connect
_recovery_codes = {}


def get_database_path():
    """Retourne le chemin local de la base sans importer de données embarquées."""
    configured = os.environ.get("SGD_DATA_DIR")
    if configured:
        data_dir = Path(configured).expanduser()
    elif sys.platform == "darwin":
        data_dir = Path.home() / "Library" / "Application Support" / "SGD" / "Data"
    elif getattr(sys, "frozen", False):
        # Sous Windows, le dossier Data est séparé du programme installé.
        data_dir = Path(sys.executable).resolve().parent / "Data"
    elif os.environ.get("LOCALAPPDATA"):
        data_dir = Path(os.environ["LOCALAPPDATA"]) / "SGD" / "Data"
    else:
        data_dir = Path.home() / "AppData" / "Local" / "SGD" / "Data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "restaurant.db"


def connect_db():
    return _sqlite_connect(str(get_database_path()), timeout=15)


def _hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS)
    return f"{_PASSWORD_SCHEME}${_PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def _is_password_hash(value):
    return isinstance(value, str) and value.startswith(_PASSWORD_SCHEME + "$")


def create_recovery_code(account, recovery_email, code):
    """Mémorise en mémoire un code de récupération court, limité dans le temps et en essais."""
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return False
    with closing(connect_db()) as conn:
        row = conn.execute("SELECT email FROM comptes WHERE nom = ?", (account,)).fetchone()
    if not row or not hmac.compare_digest(row[0].strip().casefold(), recovery_email.strip().casefold()):
        return False
    _recovery_codes[account] = {
        "digest": hashlib.sha256(code.encode("ascii")).digest(),
        "expires": time.monotonic() + 600,
        "attempts": 0,
        "verified": False,
    }
    return True


def verify_recovery_code(account, recovery_email, verification_code):
    """Valide le code envoyé par e-mail avant d'autoriser le changement de mot de passe."""
    state = _recovery_codes.get(account)
    if not state or time.monotonic() >= state["expires"] or state["attempts"] >= 5:
        _recovery_codes.pop(account, None)
        return False
    code = verification_code if isinstance(verification_code, str) else ""
    if not hmac.compare_digest(state["digest"], hashlib.sha256(code.encode("utf-8")).digest()):
        state["attempts"] += 1
        return False
    with closing(connect_db()) as conn:
        row = conn.execute("SELECT email FROM comptes WHERE nom = ?", (account,)).fetchone()
    if not row or not hmac.compare_digest(row[0].strip().casefold(), recovery_email.strip().casefold()):
        return False
    state["verified"] = True
    return True


def reset_password(account, recovery_email, new_password, verification_code=None):
    """Change le mot de passe uniquement après validation séparée du code reçu."""
    if not isinstance(new_password, str) or len(new_password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
    if not isinstance(recovery_email, str) or not recovery_email.strip():
        return False
    state = _recovery_codes.get(account)
    if not state:
        return False
    if time.monotonic() >= state["expires"] or state["attempts"] >= 5:
        _recovery_codes.pop(account, None)
        return False
    if not state.get("verified"):
        return False
    with closing(connect_db()) as conn:
        with conn:
            row = conn.execute("SELECT email FROM comptes WHERE nom = ?", (account,)).fetchone()
            if not row or not hmac.compare_digest(row[0].strip().casefold(), recovery_email.strip().casefold()):
                return False
            conn.execute(
                "UPDATE comptes SET mot_de_passe = ? WHERE nom = ?",
                (_hash_password(new_password), account),
            )
    _recovery_codes.pop(account, None)
    return True


def delete_expense(expense_id, account):
    """Supprime uniquement une dépense appartenant au compte actif."""
    with connect_db() as conn:
        cursor = conn.execute(
            "DELETE FROM depenses WHERE id = ? AND compte = ?", (expense_id, account)
        )
        return cursor.rowcount == 1


def delete_revenue(revenue_id, account):
    """Supprime uniquement un revenu appartenant au compte actif."""
    with connect_db() as conn:
        cursor = conn.execute(
            "DELETE FROM revenus WHERE id = ? AND compte = ?", (revenue_id, account)
        )
        return cursor.rowcount == 1


def get_account_email(account):
    with closing(connect_db()) as conn:
        row = conn.execute("SELECT email FROM comptes WHERE nom = ?", (account,)).fetchone()
    return row[0] if row else None


def get_expenses_for_account(account):
    with connect_db() as conn:
        return conn.execute(
            "SELECT date, montant, categorie, description, fournisseur FROM depenses WHERE compte = ? ORDER BY date DESC",
            (account,),
        ).fetchall()


def _verify_password(password, stored):
    if _is_password_hash(stored):
        try:
            scheme, rounds, salt, expected = stored.split("$", 3)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(rounds))
            return scheme == _PASSWORD_SCHEME and hmac.compare_digest(actual.hex(), expected)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(password, stored)


def set_password(account, password):
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caract?res.")
    with connect_db() as conn:
        cur = conn.execute("UPDATE comptes SET mot_de_passe=? WHERE nom=?", (_hash_password(password), account))
        return cur.rowcount == 1


def update_password(account, old_password, new_password):
    if not isinstance(new_password, str) or len(new_password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caract?res.")
    with connect_db() as conn:
        row = conn.execute("SELECT mot_de_passe FROM comptes WHERE nom=?", (account,)).fetchone()
        if not row or not _verify_password(old_password, row[0]):
            return False
        conn.execute("UPDATE comptes SET mot_de_passe=? WHERE nom=?", (_hash_password(new_password), account))
        return True

def init_db():
    """Initialise SQLite et migre les mots de passe en clair vers PBKDF2."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS depenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, montant REAL NOT NULL, categorie TEXT NOT NULL, description TEXT, fournisseur TEXT, compte TEXT NOT NULL, type_depense TEXT NOT NULL DEFAULT 'variable')")
    cursor.execute("CREATE TABLE IF NOT EXISTS comptes (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT UNIQUE NOT NULL, email TEXT NOT NULL, mot_de_passe TEXT NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS revenus (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, montant REAL NOT NULL, source TEXT NOT NULL, description TEXT, compte TEXT NOT NULL)")
    # Ne pas recr?er les anciens comptes avec des identifiants connus.
    for account_id, stored in cursor.execute("SELECT id, mot_de_passe FROM comptes").fetchall():
        if not _is_password_hash(stored):
            cursor.execute("UPDATE comptes SET mot_de_passe=? WHERE id=?", (_hash_password(stored), account_id))
    conn.commit()
    conn.close()

def get_total_depenses_pour_periode(compte, start, end):
    """Renvoie le total des dépenses pour une période donnée"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(montant) 
        FROM depenses 
        WHERE compte = ? AND date BETWEEN ? AND ?
    """, (compte, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0.0


def get_revenus_pour_periode(compte, start, end):
    """Renvoie le total des revenus du compte actif pour une période donnée"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(montant) 
        FROM revenus 
        WHERE compte = ? AND date BETWEEN ? AND ?
    """, (compte, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0.0

def get_total_depenses(compte):
    """Renvoie le total des dépenses du compte actif"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(montant) FROM depenses WHERE compte = ?", (compte,))
    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0.0


def get_depenses_par_categorie(compte):
    """Retourne une liste de tuples (categorie, total) pour le compte actif"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT categorie, SUM(montant) 
        FROM depenses 
        WHERE compte = ? 
        GROUP BY categorie 
        ORDER BY SUM(montant) DESC
    ''', (compte,))
    result = cursor.fetchall()
    conn.close()
    return result


def get_depenses_par_categorie(compte, type_cat):
    """Renvoie les dépenses par catégorie pour un type donné ('fixes' ou 'variables')"""
    conn = connect_db()
    cursor = conn.cursor()
    if type_cat == "fixes":
        categories = tuple(compte.categories_fixes)
        query = f'''
            SELECT categorie, SUM(montant) 
            FROM depenses 
            WHERE compte = ? AND categorie IN {categories}
            GROUP BY categorie 
            ORDER BY SUM(montant) DESC
        '''
    else:  # variables
        categories = tuple(compte.categories_variables)
        query = f'''
            SELECT categorie, SUM(montant) 
            FROM depenses 
            WHERE compte = ? AND categorie IN {categories}
            GROUP BY categorie 
            ORDER BY SUM(montant) DESC
        '''
    cursor.execute(query, (compte.compte_actif,))
    result = cursor.fetchall()
    conn.close()
    return result


def get_dernieres_depenses(compte, limit=5):
    """Retourne les N dernières dépenses du compte actif"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, montant, categorie, description 
        FROM depenses 
        WHERE compte = ? 
        ORDER BY date DESC LIMIT ?
    ''', (compte, limit))
    result = cursor.fetchall()
    conn.close()
    return result


def exporter_depenses_csv(compte):
    """Exporte toutes les dépenses du compte actif en CSV"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date, montant, categorie, description, fournisseur 
            FROM depenses 
            WHERE compte = ? 
            ORDER BY date DESC
        ''', (compte,))
        rows = cursor.fetchall()
        conn.close()

        filename = f'depenses_{compte}.csv'
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Montant", "Catégorie", "Description", "Fournisseur"])
            writer.writerows(rows)

        messagebox.showinfo("Export réussi", f"Fichier déposé : {filename}")
    except Exception as e:
        messagebox.showerror("Erreur", f"Échec de l'export : {e}")

def get_all_depenses_by_compte(compte):
    """Renvoie toutes les dépenses du compte actif (date, montant, categorie, fournisseur, description)"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, montant, categorie, fournisseur, description 
        FROM depenses 
        WHERE compte = ? 
        ORDER BY date DESC
    ''', (compte,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_all_depenses_filtered(self,compte, filter_type):
        """Récupère les dépenses filtrées par type (TOUT / FIXES / VARIABLES)"""
        conn = connect_db()
        cursor = conn.cursor()
        if filter_type == "TOUT":
            query = """
                SELECT date, montant, categorie, fournisseur, description 
                FROM depenses 
                WHERE compte = ? 
                ORDER BY date DESC LIMIT 10
            """
            cursor.execute(query, (compte,))
        elif filter_type == "FIXES":
            categories = tuple(compte.categories_fixes)
            placeholders = ','.join(['?'] * len(categories))
            query = f"""
                SELECT date, montant, categorie, fournisseur, description 
                FROM depenses 
                WHERE compte = ? AND categorie IN ({placeholders})
                ORDER BY date DESC LIMIT 10
            """
            cursor.execute(query, (compte,) + categories)
        else:  # VARIABLES
            categories = tuple(compte.categories_variables)
            placeholders = ','.join(['?'] * len(categories))
            query = f"""
                SELECT date, montant, categorie, fournisseur, description 
                FROM depenses 
                WHERE compte = ? type_depense = ?
                ORDER BY date DESC LIMIT 10
            """
            cursor.execute(query, (compte,filter_type))

        result = cursor.fetchall()
        conn.close()
        return result

def get_revenus_par_source(compte):
    """Retourne une liste de tuples (source, total) pour le compte actif"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT source, SUM(montant) 
        FROM revenus 
        WHERE compte = ? 
        GROUP BY source 
        ORDER BY SUM(montant) DESC
    ''', (compte,))
    result = cursor.fetchall()
    conn.close()
    return result
    
def ajouter_depense(date, montant, categorie, fournisseur, description, compte ,type_depense="variable"):
    """Ajoute une dépense dans la base de données"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO depenses (date, montant, categorie, fournisseur, description, compte ,type_depense)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (date, montant, categorie, fournisseur, description, compte, type_depense))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Erreur:", e)
        return False
    
    
def get_all_revenus_by_compte(compte):
    """Renvoie tous les revenus du compte actif (date, montant, source, description)"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, montant, source, description 
        FROM revenus 
        WHERE compte = ? 
        ORDER BY date DESC
    ''', (compte,))
    result = cursor.fetchall()
    conn.close()
    return result


def ajouter_revenu(date, montant, source, description, compte):
    """Ajoute un revenu dans la base de données"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO revenus (date, montant, source, description, compte)
            VALUES (?, ?, ?, ?, ?)
        ''', (date, montant, source, description, compte))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def ajouter_compte(nom, email, mot_de_passe):
    """Ajoute un compte apr?s validation et hachage du mot de passe."""
    if not isinstance(mot_de_passe, str) or len(mot_de_passe) < 8:
        return False
    try:
        with connect_db() as conn:
            conn.execute(
                "INSERT INTO comptes (nom, email, mot_de_passe) VALUES (?, ?, ?)",
                (nom, email, _hash_password(mot_de_passe)),
            )
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception:
        return False


def get_categories_for_type(type_finances, compte):
    """Retourne la liste des catégories uniques pour un type donné et un compte"""
    conn = connect_db()
    cursor = conn.cursor()
    if type_finances == "Dépenses":
        cursor.execute("""
            SELECT DISTINCT categorie 
            FROM depenses 
            WHERE compte = ? AND categorie IS NOT NULL 
            ORDER BY categorie
        """, (compte,))
    else:  # Revenus
        cursor.execute("""
            SELECT DISTINCT source 
            FROM revenus 
            WHERE compte = ? AND source IS NOT NULL 
            ORDER BY source
        """, (compte,))
    result = [row[0] for row in cursor.fetchall()]
    conn.close()
    return result


def verifier_connexion(nom, mot_de_passe):
    """V?rifie le mot de passe et migre un ancien hash ? la connexion."""
    with connect_db() as conn:
        row = conn.execute("SELECT id, mot_de_passe FROM comptes WHERE nom=?", (nom,)).fetchone()
        if not row or not _verify_password(mot_de_passe, row[1]):
            return False
        if not _is_password_hash(row[1]):
            conn.execute("UPDATE comptes SET mot_de_passe=? WHERE id=?", (_hash_password(mot_de_passe), row[0]))
        return True

def get_compte_defaut():
    """Retourne le premier nom de compte (ne réalise aucune authentification)."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nom FROM comptes ORDER BY id LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def get_all_comptes():
    """Récupère tous les noms de comptes"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nom FROM comptes ORDER BY nom")
    comptes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return comptes


def supprimer_depense(depense_id, compte):
    """Supprime une dépense par son ID"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM depenses WHERE id = ? AND compte = ?", (depense_id, compte))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erreur lors de la suppression de la dépense : {e}")
        return False


def supprimer_revenu(revenu_id, compte):
    """Supprime un revenu par son ID"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM revenus WHERE id = ? AND compte = ?", (revenu_id, compte))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erreur lors de la suppression du revenu : {e}")
        return False


def get_dernieres_finances(compte, limit=20):
    """Récupère les dernières finances (dépenses + revenus) triées par date décroissante"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Récupérer les dépenses
    cursor.execute('''
        SELECT id, date, montant, categorie, 'Dépense' as type, description, fournisseur
        FROM depenses 
        WHERE compte = ? 
        ORDER BY date DESC, id DESC
        LIMIT ?
    ''', (compte, limit))
    depenses = cursor.fetchall()
    
    # Récupérer les revenus
    cursor.execute('''
        SELECT id, date, montant, source as categorie, 'Revenu' as type, description, '' as fournisseur
        FROM revenus 
        WHERE compte = ? 
        ORDER BY date DESC, id DESC
        LIMIT ?
    ''', (compte, limit))
    revenus = cursor.fetchall()
    
    conn.close()
    
    # Fusionner et trier par date (décroissant)
    all_finances = depenses + revenus
    all_finances.sort(key=lambda x: (x[1], x[0]), reverse=True)  # Trier par date puis par ID
    
    return all_finances[:limit]