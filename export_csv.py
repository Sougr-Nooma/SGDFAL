import csv
from tkinter import messagebox

import database


def export_to_csv(account, output_path="depenses_export.csv"):
    """Exporte en CSV uniquement les dépenses du compte indiqué."""
    if not account:
        messagebox.showerror("Erreur", "Aucun compte actif à exporter.")
        return False

    try:
        with database.connect_db() as conn:
            rows = conn.execute(
                """SELECT id, date, montant, categorie, description, fournisseur
                   FROM depenses WHERE compte = ? ORDER BY date DESC, id DESC""",
                (account,),
            ).fetchall()

        with open(output_path, "w", newline="", encoding="utf-8") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(["ID", "Date", "Montant", "Catégorie", "Description", "Fournisseur"])
            writer.writerows(rows)

        messagebox.showinfo("Export réussi", f"Les dépenses ont été exportées dans '{output_path}'.")
        return True
    except Exception as error:
        messagebox.showerror("Erreur", f"Erreur lors de l'export : {error}")
        return False