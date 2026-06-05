# scanner.py
import omni.physx
import numpy as np
import cv2
import os
import time
#Debug: Laser anzeigen
from omni.isaac.debug_draw import _debug_draw

class ScannerSystem:
    def __init__(self):
        self._physx_query = omni.physx.get_physx_scene_query_interface()
        #Debug: Laser
        self._draw = _debug_draw.acquire_debug_draw_interface()

    def perform_fan_scan(self, current_pos):
        # Default: Leer
        is_occupied = False
        
        base_direction = np.array([-1.0, 0.0, 0.0])
        spread = np.array([0.0, 0.2, 0.0])
        offset = [base_direction, base_direction + spread, base_direction - spread]

        #Debug: Laser
        points_start = []
        points_end = []
        colors = []
        sizes = []

        for i in offset:
            # Normalisieren
            scan_direction = i / np.linalg.norm(i)

            scan_origin = current_pos + (scan_direction * 0.3)

            hit = self._physx_query.raycast_closest(scan_origin, scan_direction, 1.9)

            #Debug: Laser
            points_start.append(scan_origin)
            sizes.append(4.0)

            if hit["hit"]:
                #Debug: Laser
                hit_pos = hit["position"]
                points_end.append(np.array([hit_pos[0], hit_pos[1], hit_pos[2]]))
                colors.append((1, 0, 0, 1)) 

                if hit["distance"] < 1.9:
                    is_occupied = True
                    #break

            #Debug: Laser
            else:
                end_pos = scan_origin + (scan_direction * 1.8)
                points_end.append(end_pos)
                colors.append((0, 1, 0, 1)) 
        self._draw.draw_lines(points_start, points_end, colors, sizes)
        
        return is_occupied
    
    def read_qr_code(self, image_data):
        if image_data is None: 
            print("[DEBUG] KAMERA: Keine Bilddaten erhalten!")
            return None
        
        try:
            h, w, c = image_data.shape
            img_bgr = cv2.cvtColor(image_data, cv2.COLOR_RGBA2BGR)
            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            timestamp = int(time.time())
            debug_path = os.path.join(current_dir, f"scan_{timestamp}.png")
            #cv2.imwrite(debug_path, img_bgr)
            

            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(img_gray)
            
            if data:
                print(f"[DEBUG] QR GEFUNDEN: '{data}'")
                return data
            else:
                # CLAHE Boost
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                img_gray_boost = clahe.apply(img_gray)
                data_2, _, _ = detector.detectAndDecode(img_gray_boost)
                if data_2:
                    print(f"[DEBUG] QR (Boost) GEFUNDEN: '{data_2}'")
                    return data_2

        except Exception as e:
            print(f"[SCANNER ERROR] Bildanalyse fehlgeschlagen: {e}")
            
        return None