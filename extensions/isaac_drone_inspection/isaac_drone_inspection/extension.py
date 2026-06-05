import omni.ext
import omni.usd
import omni.kit.app
import omni.timeline
import os
import numpy as np

# Import der Module
from .config_data import Config
from .inventory import InventoryManager
from .drone_control import DroneController
from .scanner import ScannerSystem
from .states import StateMachine

class MyExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[isaac_drone_inspection] Startup (State Machine Version)")

        # Systeme initialisieren
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.inventory = InventoryManager(current_dir, Config.get_csv_filename())
        self.drone_ctrl = DroneController()
        self.scanner = ScannerSystem()
        
        # Pfad zur Auftrag Datei
        self.auftrag_file_path = os.path.join(current_dir, Config.get_auftrag_filename())

        # Waypoints generieren
        self.waypoints = []
        self._generate_waypoints()

        print(f"[INFO] Generated {len(self.waypoints)} waypoints.")
        
        # State Machine initialisieren
        self.machine = StateMachine(
            self.drone_ctrl, 
            self.scanner, 
            self.inventory, 
            self.waypoints
        )

        # Isaac Sim Events
        self._timeline = omni.timeline.get_timeline_interface()
        self._setup_done = False
        self._frames_waited = 0    

        self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
            self._on_update_event
        )

    def on_shutdown(self):
        self._update_sub = None

    def _id_to_coords(self, id_string):
        try:
            # Format: R1_P3_E2
            parts = id_string.split('_')
            r_idx = int(parts[0][1:]) - 1 # R1 -> Index 0
            p_idx = int(parts[1][1:]) - 1 # P3 -> Index 2
            e_idx = int(parts[2][1:]) - 1 # E2 -> Index 1
            
            # Koordinaten aus Config Arrays holen
            x = Config.ROW_X[r_idx]
            y = Config.SLOT_Y[p_idx]
            z = Config.HEIGHT_Z[e_idx]
            
            return np.array([x, y, z]), x # x für Reihen check
        except Exception as e:
            print(f"[ERROR] Invalid ID in auftrag file: {id_string} ({e})")
            return None, None

    def _generate_waypoints(self):

        # Modus "FULL" (Alles scannen)
        if Config.INSPECTION_MODE == "FULL":
            print("[Inspection] Mode: FULL WAREHOUSE SCAN")
            for x in Config.ROW_X:
                # Anflug
                self.waypoints.append((np.array([x, Config.SAFE_Y, 0.5]), "MOVE"))
                for z in Config.HEIGHT_Z:
                    # Ändere Hoehe
                    self.waypoints.append((np.array([x, 0.0, z]), "MOVE"))
                    for y in Config.SLOT_Y:
                        # Plätze abfliegen
                        self.waypoints.append((np.array([x, y, z]), "SCAN"))
                    # Rückflug Reihe
                    self.waypoints.append((np.array([x, 0.0, z]), "MOVE"))
                # Raus in Safe Zone
                self.waypoints.append((np.array([x, Config.SAFE_Y, 0.5]), "MOVE"))
            # Zurück an den Anfang
            self.waypoints.append((np.array([0.0, Config.SAFE_Y, 0.5]), "MOVE"))

        # Modus "FILE" (Auftrag File)
        elif Config.INSPECTION_MODE == "FILE":
            print(f"[Inspection] Mode: FILE SCAN ({self.auftrag_file_path})")

            target_ids = []

            # Datei lesen
            if os.path.exists(self.auftrag_file_path):
                with open(self.auftrag_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line: target_ids.append(line)
            else:
                print("[ERROR] Auftrag file not found")

            last_x = None # Überprüfung Reihen wechsel

            # Startpunkt
            self.waypoints.append((np.array([0.0, Config.SAFE_Y, 0.5]), "MOVE"))
            last_x = 0.0

            # Ziele verarbeiten
            for t_id in target_ids:
                coords, current_x = self._id_to_coords(t_id)
                if coords is None: continue # Skip invalid

                # check Reihenwechsel
                if last_x is not None and abs(current_x - last_x) > 0.1:
                    # Neue Reihe
                    # 1. Rausfliegen (Safe Zone bei alter Reihe)
                    self.waypoints.append((np.array([last_x, Config.SAFE_Y, 0.5]), "MOVE"))
                    # 2. Rüberfliegen (Safe Zone bei neuer Reihe)
                    self.waypoints.append((np.array([current_x, Config.SAFE_Y, 0.5]), "MOVE"))
                
                # Ziel hinzufügen
                self.waypoints.append((coords, "SCAN"))
                
                last_x = current_x

            # Am Ende: Zurück in Safe Zone
            if last_x is not None:
                self.waypoints.append((np.array([last_x, Config.SAFE_Y, 0.5]), "MOVE"))
            
            # Ganz nach Hause
            self.waypoints.append((np.array([0.0, Config.SAFE_Y, 0.5]), "MOVE"))
        # Modus "PALETTES"
        elif Config.INSPECTION_MODE == "PALETTE":
            print(f"[Inspection] Mode: PALETTEWISE")
            self.waypoints.append((np.array([0.0, Config.SAFE_Y, 0.5]), "MOVE"))
            

    def _init_simulation(self):
        print("[isaac_drone_inspection] Init Simulation & inspection")
        
        success = self.drone_ctrl.initialize_drone()
        if success:
            start_pos = self.waypoints[0][0]
            # Drohne physisch platzieren
            self.drone_ctrl.set_pose(start_pos, np.array([1,0,0,0]))
            
            # State Machine starten
            self.machine.start_inspection(start_pos)
            
            self._setup_done = True
        else:
            print("[ERROR] Init failed")

    def _on_update_event(self, e):
        # Lade Logik
        if not self._setup_done:
            self._frames_waited += 1

            # Frame 60: Datei laden
            if self._frames_waited == 60:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # Pfad 3 Ebenen hoch
                usd_path = os.path.join(current_dir, "..", "..", "..", "assets", "project_assembly.usd")

                if os.path.exists(usd_path):
                    print(f"[isaac_drone_inspection] OPENING STAGE: {usd_path}")
                    omni.usd.get_context().open_stage(usd_path)
                else:
                    print(f"[ERROR] Could not find file at {usd_path}")

             # Frame 120: Initialisieren
            elif self._frames_waited == 120:
                self._init_simulation()
            return

        # Flug Logik
        if not self._timeline.is_playing(): return
        
        # Sicherheitscheck
        if not self.drone_ctrl.drone or not self.drone_ctrl.drone.is_valid(): return
        
        dt = e.payload["dt"]
        if dt == 0: return

        # State Machine
        self.machine.update(dt)