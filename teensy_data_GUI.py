import argparse
import serial
import PySimpleGUI as sg
import threading
import random
import time

# ---------------------------------------------------------------------------- #
# Simulated function to generate test data
def simulate_teensy_data(data_dict):
    while True:
        # Generate random test data
        data_dict["battery"] = f"{random.randint(20, 100)}%"
        data_dict["speed"] = f"{random.randint(0, 120)} km/h"
        data_dict["temp"] = f"{random.randint(20, 80)}°C"
        time.sleep(0.5)  # Simulate data update every .5 sec

# ---------------------------------------------------------------------------- #
# Function to read data from Teensy
def read_teensy_data(serial_port, data_dict):
    try:
        ser = serial.Serial(serial_port, 9600, timeout=1)
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
                    print(f"Invalid data received: {line}")
    except serial.SerialException as e:
        print(f"Serial exception: {e}")
    finally:
        ser.close()

# ---------------------------------------------------------------------------- #
# Create a simple GUI to display the data
def main(use_simulation):
    # Shared data dictionary
    data = {"battery": "N/A", "speed": "N/A", "temp": "N/A"}

    # Start a thread to fetch data
    if use_simulation:
        threading.Thread(target=simulate_teensy_data, args=(data,), daemon=True).start()
    else:
        serial_port = "/dev/ttyACM0"  # Update with the correct port
        threading.Thread(target=read_teensy_data, args=(serial_port, data), daemon=True).start()

    # Define the layout for the GUI
    layout = [
        [sg.Text("Battery Percentage:", size=(20, 1), font=("Helvetica", 14)), sg.Text("", key="battery", size=(10, 1), font=("Helvetica", 14))],
        [sg.Text("Current Speed (km/h):", size=(20, 1), font=("Helvetica", 14)), sg.Text("", key="speed", size=(10, 1), font=("Helvetica", 14))],
        [sg.Text("Temperature (°C):", size=(20, 1), font=("Helvetica", 14)), sg.Text("", key="temp", size=(10, 1), font=("Helvetica", 14))],
        [sg.VPush()],  # Add vertical push to move the button to the bottom
        [sg.Button("Exit", size=(10, 1), font=("Helvetica", 14))],
    ]

    # Create the window with padding and adjusted size
    window = sg.Window(
        "Electric Car Monitor",
        layout,
        element_justification="center",
        margins=(20, 20),
        size=(400, 300)  # Increased height for better spacing
    )

    # Main event loop
    while True:
        event, _ = window.read(timeout=500)  # Update every 500ms
        if event == sg.WINDOW_CLOSED or event == "Exit":
            break

        # Update GUI with the latest data
        window["battery"].update(data["battery"])
        window["speed"].update(data["speed"])
        window["temp"].update(data["temp"])

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
