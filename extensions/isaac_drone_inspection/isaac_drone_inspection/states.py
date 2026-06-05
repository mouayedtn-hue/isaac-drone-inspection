from enum import Enum
import numpy as np
from .config_data import Config

class DroneState(Enum):
    IDLE = 0
    TAKEOFF = 1
    NAVIGATE = 2
    SCANNING = 3
    FINISHED = 4

class StateMachine:
    def __init__(self, drone_ctrl, scanner, inventory, waypoints):
        self.drone_ctrl = drone_ctrl
        self.scanner = scanner
        self.inventory = inventory
        self.waypoints = waypoints
        
        # Startzustand
        self.state = DroneState.IDLE
        
        # Navigations-Variablen
        self.current_wp_index = -1 # Startet vor dem ersten Punkt
        self.current_target_pos = None
        self.current_command = None
        self.current_drone_pos = None # Wird jeden Frame geupdated

        self.scan_timer = 0
        self.target_orientation = np.array([1, 0, 0, 0])
        self.last_move_dir = np.array([0, 1, 0])

    def start_inspection(self, start_pos):
        self.current_drone_pos = start_pos
        self.state = DroneState.TAKEOFF
        print("[Inspection] Starting Inspection -> TAKEOFF")

    def update(self, dt):
        # Position der Drohne holen
        if self.current_drone_pos is None: return

        if self.state == DroneState.IDLE:
            # Wartet auf start_inspection()
            pass

        elif self.state == DroneState.TAKEOFF:
            
            target_height = 0.5
            
            # Abheben
            if self.current_drone_pos[2] < target_height - 0.05:
                # Nur Z erhöhen
                self.current_drone_pos[2] += Config.SPEED * dt
                self.drone_ctrl.set_pose(self.current_drone_pos, np.array([1,0,0,0]))
            else:
                # Abheben fertig -> Erstes Ziel laden
                self._load_next_waypoint()
                self.state = DroneState.NAVIGATE

        elif self.state == DroneState.NAVIGATE:
            self._handle_navigation(dt)

        elif self.state == DroneState.SCANNING:
            self._handle_scanning(dt)

        elif self.state == DroneState.FINISHED:
            # Inventur abgeschlossen
            pass

    def _load_next_waypoint(self):
        self.current_wp_index += 1
        
        # Prüfen, ob Drohne am Endpunkt
        if self.current_wp_index >= len(self.waypoints):
            self.state = DroneState.FINISHED
            print("[Inspection] All waypoints visited.")
            return

        data = self.waypoints[self.current_wp_index]
        self.current_target_pos = data[0]
        self.current_command = data[1]
        

    def _handle_navigation(self, dt):
        if self.current_target_pos is None: return

        vector = self.current_target_pos - self.current_drone_pos
        dist = np.linalg.norm(vector)

        if dist > 0.05:
            move_dir = vector / dist
            
            # Blickrichtung wählen
            if self.current_command == "SCAN":
                # Beim Anflug zum Scan nach Links schauen
                self.last_move_dir = move_dir
                dx, dy = move_dir[0], move_dir[1]
                scan_look_dir = np.array([-dy, dx, 0])
                orientation = self.drone_ctrl.get_yaw_from_direction(scan_look_dir)
                self.target_orientation = orientation
            else:
                # Sonst in Flugrichtung schauen
                orientation = self.drone_ctrl.get_yaw_from_direction(move_dir)

            # Bewegen
            move_step = Config.SPEED * dt
            if move_step >= dist:
                self.current_drone_pos = self.current_target_pos
            else:
                self.current_drone_pos += (move_dir * move_step)
            
            self.drone_ctrl.set_pose(self.current_drone_pos, orientation)
        

        else:
            if self.current_command == "SCAN":

                dx, dy = self.last_move_dir[0], self.last_move_dir[1]
                scan_look_dir = np.array([-dy, dx, 0])
                self.target_orientation = self.drone_ctrl.get_yaw_from_direction(scan_look_dir)

                # Am Scan-Punkt angekommen -> Zustand wechseln
                self.scan_timer = 0
                self.state = DroneState.SCANNING
            else:
                # Nur Move-Punkt -> Direkt zum nächsten
                self._load_next_waypoint()

    def _handle_scanning(self, dt):

        self.drone_ctrl.set_pose(self.current_drone_pos, self.target_orientation)

        self.scan_timer += dt

        # Waretet auf Scan
        if self.scan_timer < 0.5:
            return

        # Scannen
        is_occupied = self.scanner.perform_fan_scan(self.current_drone_pos)
        status_text = "LEER"

        if is_occupied:

            image = self.drone_ctrl.get_camera_frame()
            qr_code = self.scanner.read_qr_code(image)

            if qr_code:
                # QR Code gefunden
                status_text = f"Artikel: {qr_code}"
            else:
                # Paket da, aber kein QR lesbar
                status_text = "BELEGT (Kein QR)"


        pos = self.current_target_pos
        
        # ID berechnen
        Reihe = int(pos[0] / 5) + 1
        Platz = int(pos[1] / 4) + 1
        Etage = 1 if pos[2] == 0.5 else 2 if pos[2] == 1.7 else 3

        # Speichern
        self.inventory.update_entry(Reihe, Platz, Etage, status_text)
        print(f"[INSPECTION] Reihe: {Reihe} | Platz: {Platz} | Etage: {Etage} -> {status_text}")

        # Fertig -> Weiterfliegen
        self._load_next_waypoint()
        self.state = DroneState.NAVIGATE