"""
    Description: Simple PySimpleGUI application to read data published by our Teensy
    DAQ system to raspberry pi serial and display it easily to driver
    Author: SCU FSAE Electrical Subteam
    Date: Winter 2025
"""

"""
TODO:
1. Possibly add CPU usage / other usage stats ported from teensy to monitor DAQ /
overall health of car peripherals and processors
"""


import argparse
import serial
import PySimpleGUI as sg
import threading
import random
import time

SIM_ARTIFICIAL_DELAY = 1  # artificial delay for simulated data in seconds

# ---------------------------------------------------------------------------- #
# Simulated function to generate test data
def simulate_teensy_data(data_dict, error_flag):
    while True:
        if error_flag["status"]:  # Skip updating if there's an error
            time.sleep(SIM_ARTIFICIAL_DELAY)
            continue

        # Generate random test data
        data_dict["battery"] = f"{random.randint(20, 100)}%"
        data_dict["speed"] = f"{random.randint(0, 120)} km/h"
        data_dict["temp"] = f"{random.randint(20, 80)}°C"
        data_dict["error"] = "No errors detected."
        time.sleep(SIM_ARTIFICIAL_DELAY)  # Simulate data update every second


# ---------------------------------------------------------------------------- #
# Function to read data from Teensy
def read_teensy_data(serial_port, data_dict, error_flag):
    try:
        ser = serial.Serial(serial_port, 9600, timeout=1)
        error_flag["status"] = False  # Clear error status if successful
        while True:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8').strip()
                # Parse the data (expected format: "battery:80,speed:40,temp:25")
                try:
                    parts = line.split(',')
                    for part in parts:
                        key, value = part.split(':')
                        data_dict[key] = value
                except ValueError:
                    data_dict["error"] = f"Invalid data received: {line}"
                    error_flag["status"] = True
    except serial.SerialException as e:
        data_dict["error"] = f"Serial exception: {e}"
        error_flag["status"] = True
    finally:
        ser.close()

# ---------------------------------------------------------------------------- #
# Create a simple GUI to display the data
def main(use_simulation):
    # Shared data dictionary and error flag
    data = {"battery": "N/A", "speed": "N/A", "temp": "N/A", "error": "Initializing..."}
    error_flag = {"status": False}

    # Start a thread to fetch data
    def start_data_thread():
        if use_simulation:
            threading.Thread(target=simulate_teensy_data, args=(data, error_flag), daemon=True).start()
        else:
            serial_port = "/dev/ttyACM0"  # Update with the correct port
            threading.Thread(target=read_teensy_data, args=(serial_port, data, error_flag), daemon=True).start()

    start_data_thread()

    # Define the layout for the GUI
    layout = [
        [sg.Text("Battery Percentage:", size=(20, 1), font=("Helvetica", 14)), sg.Text("", key="battery", size=(10, 1), font=("Helvetica", 14))],
        [sg.Text("Current Speed (km/h):", size=(20, 1), font=("Helvetica", 14)), sg.Text("", key="speed", size=(10, 1), font=("Helvetica", 14))],
        [sg.Text("Temperature (°C):", size=(20, 1), font=("Helvetica", 14)), sg.Text("", key="temp", size=(10, 1), font=("Helvetica", 14))],
        [sg.Text("Error Status:", size=(20, 1), font=("Helvetica", 14)), sg.Text("", key="error", size=(30, 1), font=("Helvetica", 14), text_color="red")],
        [sg.Text("Application Status:", size=(20, 1), font=("Helvetica", 14)), sg.Text("", key="status", size=(30, 1), font=("Helvetica", 14), text_color="blue")],
        [sg.VPush()],
        [sg.Button("Reboot", size=(10, 1), font=("Helvetica", 14)), sg.Button("Exit", size=(10, 1), font=("Helvetica", 14))],
    ]

    # Create the window
    window = sg.Window(
        "Electric Car Monitor",
        layout,
        element_justification="center",
        margins=(20, 20),
        size=(500, 400)  # Adjusted size for additional status message
    )

    # Main event loop
    while True:
        event, _ = window.read(timeout=500)  # Update every 500ms
        if event == sg.WINDOW_CLOSED or event == "Exit":
            break

        if event == "Reboot":
            error_flag["status"] = False  # Clear error flag
            data["error"] = "Rebooting data collection..."
            window["error"].update(data["error"])
            window["status"].update("Rebooting...", text_color="orange")
            start_data_thread()  # Restart the data collection thread

        # Update GUI with the latest data
        window["battery"].update(data["battery"])
        window["speed"].update(data["speed"])
        window["temp"].update(data["temp"])
        window["error"].update(data["error"])

        # Update application status
        if error_flag["status"]:
            window["status"].update("Errored", text_color="red")
        elif data["error"] == "Rebooting data collection...":
            window["status"].update("Rebooting...", text_color="orange")
        else:
            window["status"].update("Active", text_color="green")

    window.close()

# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Electric Car Monitor")
    parser.add_argument(
        "-test",
        action="store_true",
        help="Use simulated data instead of real data from USB"
    )
    args = parser.parse_args()

    # Run the main function with the appropriate data source
    main(use_simulation=args.test)
