"""
    Description: Simple PySimpleGUI application to read data published by our Teensy
    DAQ system to raspberry pi serial and display it easily to driver
    Author: SCU FSAE Electrical Subteam
    Date: Winter 2025
"""

# Usage:
# Teensy hooked up to Raspi on port, get port name and set it below
# pip3 install -r requirements.txt
# python3 teensy_data_GUI.py (OPTIONAL FLAG -test)

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

SIM_ARTIFICIAL_DELAY = 0.3  # artificial delay for simulated data in seconds
batteryLevel = 100
SERIAL_BAUDRATE = 9600 # set to this in the Teensy publisher

# ---------------------------------------------------------------------------- #
# Simulated function to generate test data
def simulate_teensy_data(data_dict, error_flag):
    global batteryLevel
    while True:
        if error_flag["status"]:  # Skip updating if there's an error
            time.sleep(SIM_ARTIFICIAL_DELAY)
            continue

        # Generate random test data
        data_dict["battery"] = f"{batteryLevel}"
        data_dict["speed"] = f"{random.randint(0, 120)}"
        data_dict["power"] = f"{random.randint(0, 120)}"
        data_dict["RPM"] = f"{random.randint(5000, 11000)}"
        data_dict["temp"] = f"{random.randint(20, 80)}°C"
        data_dict["error"] = "All \n Clear"
        time.sleep(SIM_ARTIFICIAL_DELAY)  # Simulate data update every second
        batteryLevel -= 1


# ---------------------------------------------------------------------------- #
# Function to read data from Teensy
def read_teensy_data(serial_port, data_dict, error_flag):
    try:
        ser = serial.Serial(serial_port, SERIAL_BAUDRATE, timeout=1)
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
    #finally:
        #ser.close()

# ---------------------------------------------------------------------------- #
# Create a simple GUI to display the data
def main(use_simulation):
    # Shared data dictionary and error flag
    data = {"battery": "N/A", "RPM": "N?A", "power": "N?A", "speed": "N/A", "temp": "N/A", "error": "Initializing..."}
    error_flag = {"status": False}
    global batteryLevel

    # Start a thread to fetch data
    def start_data_thread():
        if use_simulation:
            threading.Thread(target=simulate_teensy_data, args=(data, error_flag), daemon=True).start()
        else:
            serial_port = "/dev/ttyACM0"  # Update with the correct port
            threading.Thread(target=read_teensy_data, args=(serial_port, data, error_flag), daemon=True).start()

    start_data_thread()

    col1 = sg.Column([[sg.Text("TS1:",  font=("Helvetica", 30)), sg.Text("", key="temp", size=(5, 1), font=("Helvetica", 30))],
                      [sg.Text("TS2:",  font=("Helvetica", 30)), sg.Text("", key="temp", size=(5, 1), font=("Helvetica", 30))],
                      [sg.Text("TS3:",  font=("Helvetica", 30)), sg.Text("", key="temp", size=(5, 1), font=("Helvetica", 30))],
                      [sg.Text("TS4:",  font=("Helvetica", 30)), sg.Text("", key="temp", size=(5, 1), font=("Helvetica", 30))],
                      [sg.Text("PWR:",  font=("Helvetica", 30)), sg.Text("", key="power", size=(5, 1), font=("Helvetica", 30))]], pad=0)
    col2 = sg.Column([[sg.Text(key="speed", size=(2,1), font=("Helvetica", 100))],
                      [sg.Text("MPH", font=("Helvetica", 30))],
                      [sg.Text(key="RPM", size=(5,1), font=("Helvetica", 100))],
                      [sg.Text("RPM", font=("Helvetica", 30))]], pad=0)
    col3 = sg.Column([[sg.Text(key="error", font=("Helvetica", 50), expand_y = (False), text_color="lime")]], pad=0)
    
    # Define the layout for the GUI
    layout = [
        [col1, sg.VerticalSeparator(), sg.Push(), col2, sg.Push(), sg.VerticalSeparator(), col3],
        [sg.VPush()],
        [sg.ProgressBar(100, orientation='h', expand_x = True, size_px=(800, 40), bar_color = ("yellow","gray"), key='-PBAR-')], 
    ]

    # Create the window
    window = sg.Window(
        "Electric Car Monitor",
        layout,
        element_justification="center",
        size=(800, 480)  # size of raspi 7in display in pixels
    )

    # Main event loop
    while True:
        event, _ = window.read(timeout=300)  # Update every 500ms
        if event == sg.WINDOW_CLOSED or event == "Exit":
            break

        if event == "Reboot":
            error_flag["status"] = False  # Clear error flag
            data["error"] = "Rebooting data collection..."
            window["error"].update(data["error"])
            window["status"].update("Rebooting...", text_color="orange")
            start_data_thread()  # Restart the data collection thread

        if batteryLevel <= 0:
            error_flag["status"] = True
            data["error"] = "Battery \n Dead"
            window["error"].update(data["error"], text_color="red")

        # Update GUI with the latest data
        window["speed"].update(data["speed"])
        window["RPM"].update(data["RPM"])
        window["power"].update(data["power"])
        window["temp"].update(data["temp"])
        window["error"].update(data["error"])
        window['-PBAR-'].update(current_count = batteryLevel)

        # Update application status

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
