import omni.usd
import math
import numpy as np
from omni.isaac.core.prims import XFormPrim
from pxr import UsdPhysics, Usd, UsdGeom, Gf 
from omni.isaac.sensor import Camera

class DroneController:
    def __init__(self):
        self.drone = None
        self.drone_path = None
        self.camera = None

    def initialize_drone(self):
        # Drohne suchen
        self.drone_path = self._find_drone_path()
        
        if not self.drone_path:
            print("[ERROR] No drone found in the opened stage!")
            return False

        print(f"[SUCCESS] Found drone at: {self.drone_path}")

        # Physik sicher deaktivieren
        self._nuke_robot_physics(self.drone_path)
        
        # Objekt referenzieren
        self.drone = XFormPrim(prim_path=self.drone_path, name="drone")

        # Kamera montieren
        if self.drone.is_valid():
            self._setup_camera()
            return True
        return False

    def set_pose(self, position, orientation):
        if self.drone and self.drone.is_valid():
            self.drone.set_world_pose(position=position, orientation=orientation)

    def get_camera_frame(self):
        if self.sensor_camera:
            # Holt das aktuelle RGBA Bild als Numpy Array
            return self.sensor_camera.get_rgba()
        return None

    def get_yaw_from_direction(self, direction):
        dx, dy = direction[0], direction[1]
        if abs(dx)<0.001 and abs(dy)<0.001: return np.array([1,0,0,0]) 
        yaw = math.atan2(dy, dx)
        half = yaw / 2
        return np.array([math.cos(half), 0, 0, math.sin(half)])

    def _find_drone_path(self):
        # Sucht nach der Drohne in der gesamten Stage
        stage = omni.usd.get_context().get_stage()
        if not stage: return None
        
        print("[INFO] Scanning stage for 'cf2x'...")
        for prim in stage.Traverse():
            if prim.GetName() == "cf2x":
                return prim.GetPath().pathString
        return None

    def _setup_camera(self):
        stage = omni.usd.get_context().get_stage()
        
        camera_name = "Camera" 
        camera_path = f"{self.drone_path}/{camera_name}"
        
        if not stage.GetPrimAtPath(camera_path):
             print(f"[INFO] '{camera_name}' not found. Creating new 'onboard_camera'...")
             camera_path = f"{self.drone_path}/onboard_camera"

        self.camera = UsdGeom.Camera.Define(stage, camera_path)
        xform_cam = UsdGeom.Xformable(self.camera)
        
        xform_cam.ClearXformOpOrder() 
        
        # Position: 20cm vor der Drohne
        xform_cam.AddTranslateOp().Set(Gf.Vec3d(0.2, 0.0, 0.0))
        # Rotation: Damit sie nach vorne schaut
        xform_cam.AddRotateXYZOp().Set(Gf.Vec3d(90, 0, -90))

        # Sensor Objekt initialisieren
        self.sensor_camera = Camera(prim_path=camera_path, resolution=(1920, 1080))
        self.sensor_camera.initialize()

    def _nuke_robot_physics(self, prim_path):
        # Sichere Methode um Physik zu deaktivieren
        stage = omni.usd.get_context().get_stage()
        if not stage: return
        
        root_prim = stage.GetPrimAtPath(prim_path)
        if not root_prim.IsValid(): return

        # Pfade sammeln
        paths_to_modify = []
        def collect_recursive(current_prim):
            paths_to_modify.append(current_prim.GetPath())
            for child in current_prim.GetChildren():
                collect_recursive(child)
        
        collect_recursive(root_prim)
            
         # Modifizieren
        for path in paths_to_modify:
            p = stage.GetPrimAtPath(path)
            if not p.IsValid(): continue
            
            if p.HasAPI(UsdPhysics.ArticulationRootAPI):
                p.RemoveAPI(UsdPhysics.ArticulationRootAPI)

            if p.IsA(UsdPhysics.Joint):
                p.SetActive(False)

            if p.HasAPI(UsdPhysics.RigidBodyAPI):
                rb = UsdPhysics.RigidBodyAPI(p)
                rb.CreateKinematicEnabledAttr(True)