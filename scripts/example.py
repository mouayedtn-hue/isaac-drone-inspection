from omni.isaac.kit import SimulationApp


simulation_app = SimulationApp({"headless": False})


from omni.isaac.core.utils.extensions import enable_extension


enable_extension("isaac_drone_inspection")


while simulation_app.is_running():
    simulation_app.update()

simulation_app.close()
