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
BAUD_RATE = 9600

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
    if not handshake:
        try:
            if line.strip().lower() == "shutdown":
                close_app(shutdown=1)
                return
            
            if "=" not in line:
                return
            key, value = line.strip().split("=")

            if key == "motor_speed":
                speed_lbl.config(text=f"Min: {float[value]} V")
                fill_w = int((int(value) / MAX_RPM) * bar_w_max)
                bar_canvas.delete("all")
                bar_canvas.create_rectangle(0, 0, fill_w, bar_h, fill="lime", width=0)

            elif key == "power":
                power_lbl.config(text=f"Min: {float[value]} V")

            
            elif key == "acc_voltage":
                acc_lbl.config(text=f"ACC: {float(value)} V")
            
            elif key == "min_voltage":
                color = "red" if value <= min_voltage_threshold else "white"
                min_voltage_lbl.config(text=f"Min: {float[value]} V", fg=color)

            elif key == "max_voltage":
                max_voltage_lbl.config(text=f"Max: {float(value)} V")
            
            elif key == "acc_temp":
                color = "red" if value >= max_acc_temp_threshold else "white"
                acc_temp_lbl.config(text=f"Tmp: {float(value)} °C")

            elif key == "motor_temp":
                color = "red" if value >= max_motor_temp_threshold else "white"
                motor_temp_lbl.config(text=f"Mtr Tmp: {float(value)} °C")

            elif key == "controller_temp":
                color = "red" if value >= max_controller_temp_threshold else "white"
                motor_cnt_temp_lbl.config(text=f"Cnt Tmp: {float(value)} °C")

            elif key == "coolant_temp":
                color = "red" if value >= max_coolant_temp_threshold else "white"
                coolant_temp_lbl.config(text=f"Cool Tmp: {float(value)} °C")
            
            elif key == "drive_state":
                color = "green" if value == 1 else "red"
                message = "Enabled" if value == 1 else "Ready to Drive"
                state_lbl.config(text=message)
                
        except Exception as e:
            print("Serial parse error:", e)

# ——————————————————
# Reads Serial Data
# ——————————————————
def read_serial_continuously():
    try:
        while ser.in_waiting:
            line = ser.readline().decode("utf-8").strip()
            if line:
                handle_serial_line(line)
    except Exception as e:
        print("Serial read error:", e)

    root.after(10, read_serial_continuously)

# ———————————————————————————————
# Waits for teensy communication
# ———————————————————————————————
def wait_for_teensy():
    try:
        ser.write(b'READY\n')
        if ser.in_waiting:
            response = ser.readline().decode().strip()
            if response == "READY":
                state_lbl.config(text="INITIALIZING")
                return
    except Exception as e:
        print("Handshake error:", e)

    root.after(1000, wait_for_teensy)

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

    # Clear motor speed bar
    bar_canvas.delete("all")

# ———————————————————
# Fake data generator
# ———————————————————
def generate_fake_data():
    return {
        "motor_speed": random.randint(0, MAX_RPM),
        "power": round(random.uniform(30, 50), 2),
        "acc_voltage": round(random.uniform(350, 435), 1),
        "min_voltage": round(random.uniform(1.2, 2.0), 3),
        "max_voltage": round(random.uniform(3.7, 4.2), 3),
        "coolant_temp": round(random.uniform(20, 90), 1),
        "motor_temp": round(random.uniform(20, 90), 1),
        "controller_temp": round(random.uniform(20, 90), 1)
    }

# ————————————————
# Set Widget Text
# ————————————————
def set_text(widget, label, val):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", label, "label")
        widget.insert("end", val, "data")
        widget.config(state="disabled")

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

# Inner content frame with margin (the actual dashboard)
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
# Update Loop
# ————————————————
def update_dashboard():
    data = generate_fake_data()  

    # 1) redraw bar
    bar_canvas.delete("all")
    fill_w = int((data["motor_speed"] / MAX_RPM) * bar_w_max)
    bar_canvas.create_rectangle(0, 0, fill_w, bar_h, fill="lime", width=0)

    # 2) update text
    speed_lbl.config(text=f"{data['motor_speed']} rpm")
    power_lbl.config(text=f"Power: {data['power']:.3f} W")
    min_voltage_lbl.config(text=f"Min: {data['min_voltage']} V")
    acc_lbl.config(text=f"{data['acc_voltage']} V")
    acc_temp_lbl.config(text=f"Acc Tmp:{data['acc_temp']} °C")
    max_voltage_lbl.config(text=f"Max: {data['max_voltage']} V")
    motor_temp_lbl.config(text=f"Mtr Tmp: {data['motor_temp']} °C")
    motor_cnt_temp_lbl.config(text=f"Cnt Tmp: {data['controller_temp']} °C")
    coolant_temp_lbl.config(text=f"Cool Tmp: {data['coolant_temp']} °C")

    root.after(1000, update_dashboard)

# ————————————————
# Exit on ESC
# ————————————————
root.bind("<Escape>", lambda event: close_app())

# ————————————————
# Start
# ————————————————
#update_dashboard()
show_placeholder_data()
root.after(1000, wait_for_teensy)
root.after(100, read_serial_continuously)
root.mainloop()
