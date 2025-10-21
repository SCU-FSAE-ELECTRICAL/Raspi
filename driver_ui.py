import os
import tkinter as tk
import random
import serial
import time
from PIL import Image, ImageTk

# ————————————————
# CONFIG
# ————————————————
MAX_RPM = 800
BORDER_THICKNESS = 10
SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 19200

handshake = False
min_voltage_threshold = 1.0
max_motor_temp_threshold = 100
max_controller_temp_threshold = 100
max_coolant_temp_threshold = 90
max_acc_temp_threshold = 90

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except serial.SerialException as e:
    print("Serial port error: ", e)
    exit(1)

# ——————————————————————
# Closes the application
# ——————————————————————
def close_app(shutdown=0):
    try:
        if ser.is_open:
            ser.close()
            print("✅ Serial port closed.")
    except Exception as e:
        print("⚠️ Error closing serial port:", e)
    finally:
        root.destroy()
    
    if shutdown:
        os.system("sudo shutdown now")

# ——————————————————————
# Interprets Serial Data
# ——————————————————————
def handle_serial_line(line):
    global handshake
    try:
        if not handshake:
            # Before handshake, only listen for shutdown command
            if line.strip().lower() == "shutdown":
                close_app(shutdown=1)
            return
        
        if "=" not in line:
            return
        key, value = line.strip().split("=")
        value = float(value)

        if key == "mtr_s":
            speed_lbl.config(text=f"{value:.0f} RPM")
            fill_w = int((value / MAX_RPM) * bar_w_max)
            bar_canvas.delete("all")
            bar_canvas.create_rectangle(0, 0, fill_w, bar_h, fill="lime", width=0)

        elif key == "pwr":
            power_lbl.config(text=f"Power: {value:.2f} W")

        elif key == "acc_v":
            acc_lbl.config(text=f"{value:.1f} V")
        
        elif key == "min_v":
            color = "red" if value <= min_voltage_threshold else "white"
            min_voltage_lbl.config(text=f"Min: {value:.3f} V", fg=color)

        elif key == "max_v":
            max_voltage_lbl.config(text=f"Max: {value:.3f} V")
        
        elif key == "acc_t":
            color = "red" if value >= max_acc_temp_threshold else "white"
            acc_temp_lbl.config(text=f"Acc Tmp: {value:.1f} °C", fg=color)

        elif key == "mtr_t":
            color = "red" if value >= max_motor_temp_threshold else "white"
            motor_temp_lbl.config(text=f"Mtr Tmp: {value:.1f} °C", fg=color)

        elif key == "cnt_t":
            color = "red" if value >= max_controller_temp_threshold else "white"
            motor_cnt_temp_lbl.config(text=f"Cnt Tmp: {value:.1f} °C", fg=color)

        elif key == "cool_t":
            color = "red" if value >= max_coolant_temp_threshold else "white"
            coolant_temp_lbl.config(text=f"Cool Tmp: {value:.1f} °C", fg=color)
        
        elif key == "status":
            color = "green" if value == 1 else "red"
            message = "Enabled" if value == 1 else "Ready to Drive"
            state_lbl.config(text=message, fg=color)
                
    except Exception as e:
        print("Serial parse error:", e)

# ——————————————————
# Reads Serial Data
# ——————————————————
def read_serial_continuously():
    try:
        while ser.in_waiting:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                handle_serial_line(line)
    except Exception as e:
        print("Serial read error:", e)

    root.after(10, read_serial_continuously)

# ———————————————————————————————
# Waits for teensy communication
# ———————————————————————————————
def wait_for_teensy():
    global handshake
    try:
        ser.write(b'pi_ready\n')
        time.sleep(0.3)

        if ser.in_waiting:
            response = ser.readline().decode(errors="ignore").strip().lower()
            print(f"Handshake response: '{response}'")
            if "rodger" in response:
                handshake = True
                state_lbl.config(text="INITIALIZING", fg="lime")
                print("✅ Handshake successful.")
                root.after(100, read_serial_continuously)
                return
    except Exception as e:
        print("Handshake error:", e)

    print("❌ Handshake failed. Retrying...")
    root.after(1000, wait_for_teensy)

# —————————————————————————————————————————
# Sends serial check confirmation to teensy
# —————————————————————————————————————————
def sendCheck():
    try:
        ser.write(b"check\n")
    except Exception as e:
        print(e)

# ————————————————————————————————————————————————
# Placeholder until data is recived over serial
# ————————————————————————————————————————————————
def show_placeholder_data():
    speed_lbl.config(text="### rpm")
    power_lbl.config(text="Power: ### W")
    min_voltage_lbl.config(text="Min: ### V")
    acc_lbl.config(text="### V")
    acc_temp_lbl.config(text="Acc Tmp: ### °C")
    max_voltage_lbl.config(text="Max: ### V")
    motor_temp_lbl.config(text="Mtr Tmp: ### °C")
    motor_cnt_temp_lbl.config(text="Cnt Tmp: ### °C")
    coolant_temp_lbl.config(text="Cool Tmp: ### °C")
    bar_canvas.delete("all")

# ————————————————
# Force Fullscreen
# ————————————————
def wait_for_fullscreen():
    if root.attributes("-fullscreen"):
        print("✅ Fullscreen is active.")
        return
    else:
        print("❌ Not fullscreen yet. Retrying...")
        root.attributes("-fullscreen", True)
        root.after(1000, wait_for_fullscreen)

# —————
# Main
# —————
root = tk.Tk()
root.attributes('-fullscreen', True)
root.configure(bg="#660000")
root.after(100, wait_for_fullscreen)

SCREEN_W = root.winfo_screenwidth()
SCREEN_H = root.winfo_screenheight()

# Border frame
border_frame = tk.Frame(root, bg="#660000")
border_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

# Inner content frame
inner_frame = tk.Frame(border_frame, bg="black")
inner_frame.place(
    x=BORDER_THICKNESS,
    y=BORDER_THICKNESS,
    width=SCREEN_W - 2 * BORDER_THICKNESS,
    height=SCREEN_H - 2 * BORDER_THICKNESS
)

# ———————————————————
# Bar for motor speed
# ———————————————————
bar_h = 50
bar_w_max = 700
bar_canvas = tk.Canvas(inner_frame, bg="gray20", highlightthickness=0)
bar_canvas.place(x=30, y=20, width=bar_w_max, height=bar_h)

# —————————————————
# Gauges underneath
# —————————————————
font_14 = ("Mono 91", 14)
font_20 = ("Mono 91", 20)
font_22 = ("Mono 91", 22)
font_26 = ("Mono 91", 26)
font_36 = ("Mono 91", 36)

# Left column
speed_frame = tk.Frame(inner_frame, bg="black")
speed_frame.place(x=30, y=90)
speed_text = tk.Label(speed_frame, text="Motor Speed: ", font=font_20, fg="white", bg="black")
speed_text.pack(side="left")
speed_lbl = tk.Label(speed_frame, text="### rpm", font=font_36, fg="white", bg="black")
speed_lbl.pack(side="left")

power_lbl = tk.Label(inner_frame, text="", font=font_22, fg="white", bg="black")
power_lbl.place(x=30, y=150)

motor_temp_lbl = tk.Label(inner_frame, text="", font=font_14, fg="white", bg="black")
motor_temp_lbl.place(x=30, y=190)

motor_cnt_temp_lbl = tk.Label(inner_frame, text="", font=font_14, fg="white", bg="black")
motor_cnt_temp_lbl.place(x=30, y=215)

coolant_temp_lbl = tk.Label(inner_frame, text="", font=font_14, fg="white", bg="black")
coolant_temp_lbl.place(x=30, y=240)

# Right column
min_voltage_lbl = tk.Label(inner_frame, text="", font=font_20, fg="white", bg="black")
min_voltage_lbl.place(x=500, y=150)

max_voltage_lbl = tk.Label(inner_frame, text="", font=font_20, fg="white", bg="black")
max_voltage_lbl.place(x=500, y=190)

acc_frame = tk.Frame(inner_frame, bg="black")
acc_frame.place(x=500, y=90)
acc_text = tk.Label(acc_frame, text="ACC: ", font=font_20, fg="white", bg="black")
acc_text.pack(side="left")
acc_lbl = tk.Label(acc_frame, text="### V", font=font_36, fg="white", bg="black")
acc_lbl.pack(side="left")

acc_temp_lbl = tk.Label(inner_frame, text="", font=font_14, fg="white", bg="black")
acc_temp_lbl.place(x=630, y=170)

# —————————————————————
# State at bottom left
# —————————————————————
state_lbl = tk.Label(
    inner_frame,
    text="Waiting for Serial Connection",
    font=("Mono 91", 28, "bold"),
    fg="yellow",
    bg="black"
)
state_lbl.place(relx=0.025, rely=1.0, y=-30, anchor="sw")

# ——————————————————————————————————
# Bronco Racing Logo (bottom right)
# ——————————————————————————————————
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(script_dir, "splash.png")
    img = Image.open(logo_path)
    img = img.resize((100, 100), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    logo_lbl = tk.Label(inner_frame, image=photo, bg="black")
    logo_lbl.image = photo
    logo_lbl.place(x=SCREEN_W - 2 * BORDER_THICKNESS - 115, y=SCREEN_H - 2 * BORDER_THICKNESS - 115)
except Exception as e:
    print("Logo load error:", e)

# ————————————————
# Exit on ESC
# ————————————————
root.bind("<Escape>", lambda event: close_app())

# ————————————————
# Start sequence
# ————————————————
show_placeholder_data()
root.after(1000, wait_for_teensy)
root.after(500, sendCheck)
root.mainloop()
