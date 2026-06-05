import numpy as np

class Config:
    # Konfiguration 
    SPEED = 1.5 

    # Modus: "FULL" (Alles scannen) oder "FILE" (auftrag.txt lesen)
    INSPECTION_MODE = "PALETTE"
    
    # Punkt um die Reihen zu wechseln
    SAFE_Y = -4.0

    # Lager Layout
    # Reihen
    ROW_X = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0]
    # Plätze
    SLOT_Y = [0.0, 4.0, 8.0, 12.0]
    # Etage
    HEIGHT_Z = [0.5, 1.7, 3.2]


    @staticmethod
    def get_csv_filename():
        return "warehouse_inventory.csv"
    
    @staticmethod
    def get_auftrag_filename():
        return "auftrag.txt"