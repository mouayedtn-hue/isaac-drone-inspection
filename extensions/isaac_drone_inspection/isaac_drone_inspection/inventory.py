import os
import csv
from datetime import datetime

class InventoryManager:
    def __init__(self, base_path, filename):
        # Csv Datei Pfad
        self.csv_file_path = os.path.join(base_path, filename)
        # Interner Speicher
        self.inventory_data = {}
        
        # Direkt laden
        self._load_or_create_csv()

    def _load_or_create_csv(self):
        # Prüfen ob Datei exestiert
        if os.path.exists(self.csv_file_path):
            print(f"[CSV] Loading existing inventory from {self.csv_file_path}")
            try:
                with open(self.csv_file_path, mode='r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Datei in Speicher laden
                        if "ID" in row:
                            self.inventory_data[row["ID"]] = row
            except Exception as e:
                print(f"[ERROR] Could not read CSV: {e}")
        else:
            print(f"[CSV] Creating new inventory file at {self.csv_file_path}")
            # Leere Datei mit Header erstellen
            self._write_csv_file()

    def update_entry(self, r, p, e, status):
        # ID generierung
        slot_id = f"R{r}_P{p}_E{e}"

        # Datum und Zeit
        now = datetime.now()

        # Daten in Speicher packen
        self.inventory_data[slot_id] = {
            "ID": slot_id,
            "Reihe": r,
            "Platz": p,
            "Etage": e,
            "Status": status,
            "Datum": now.strftime("%Y.%m.%d"),    # 2025.12.12
            "Uhrzeit": now.strftime("%H:%M:%S")   # 14:30:05
        }

        # Datei sofort überschreiben
        self._write_csv_file()

    def _write_csv_file(self):
        # Schreibt alles in die Datei
        header = ["ID", "Reihe", "Platz", "Etage", "Status", "Datum", "Uhrzeit"]

        try:
            with open(self.csv_file_path, mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                # Sortiert nach ID
                for key in sorted(self.inventory_data.keys()):
                    writer.writerow(self.inventory_data[key])
        except Exception as err:
            print(f"[ERROR] Writing CSV failed: {err}")