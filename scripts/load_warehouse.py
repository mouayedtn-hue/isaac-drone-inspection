from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False})

import os
import sys
from omni.isaac.core import World
from omni.isaac.core.utils.stage import add_reference_to_stage

def main():
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    usd_path = os.path.join(project_root, "..", "assets", "project_assembly.usd")

    if not os.path.exists(usd_path):
        print(f"[ERROR] Could not find file at: {usd_path}")
        print("Check that your file structure matches: isaac-drone-inspection/assets/project_assembly.usd")
        simulation_app.close()
        return

    print(f"[INFO] Loading Main Assembly from: {usd_path}")


    world = World()

    add_reference_to_stage(usd_path=usd_path, prim_path="/World/Environment")


    world.reset()
    print("[INFO] Simulation is running. Press Ctrl+C in terminal to stop.")

    while simulation_app.is_running():
        world.step(render=True)

    simulation_app.close()

if __name__ == "__main__":
    main()