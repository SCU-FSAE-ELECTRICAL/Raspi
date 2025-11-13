import os
import tkinter as tk
import serial
import time
import math
from PIL import Image, ImageTk
from collections import deque

# ————————————————
# CONFIG
# ————————————————
MAX_RPM = 800
BORDER_THICKNESS = 10

#SERIAL_PORT = "/dev/serial0"
#BAUD_RATE = 19200

handshake = False
min_voltage_threshold = 1.0
max_motor_temp_threshold = 100
max_controller_temp_threshold = 100
max_coolant_temp_threshold = 90
max_acc_temp_threshold = 90

# ————————————————
# Faults Dictionary
# ————————————————
faults = {
    "BMS": 0, #Battery management system (Critical)
    "IMD": 0, #Insulation monitoring device (Critical)
    "BSPD": 0, #Brake system plausibility device (Critical)
    "MC" : 0, #Motor Controller/inverter fault (Critical)
    "REAR_TEENSY": 0, #Check if Rear-Teensy is connected (Critical)
    "SDCARD": 0, #SD activity (Non-Critical)
    "ACCEL": 0, #accelerator warning (Non-Critical)
    "INTERLOCK": 0,
    "TSMS": 0, #Tractive System master Switch
    "GLVMS": 0, #Grounded Low-Voltage Master Switch
    "SDBTN": 0, #Shutdown Button
    "BOTS": 0 #Brake Over-Travel Switch
}

CRITICAL_KEYS   = ["IMD", "BMS", "BSPD", "MC", "REAR_TEENSY"]
NONCRITICAL_KEYS = ["SDCARD", "ACCEL"]

def any_critical_active():
    return any(faults[k] == 1 for k in CRITICAL_KEYS)

def any_noncritical_active():
    return any(faults[k] == 1 for k in NONCRITICAL_KEYS)

# ————————————————
# UI State Flags Dictionary
# ————————————————
state_flags = {
    "status": 0,          # 0=not enabled, 1=enabled (from Teensy)
    "ts_active": 0,       # 0=SDC open, 1=SDC closed / tractive armed
    "manual_reset_ok": 0, # manual reset latch cleared
    "brk": 0,
    "gas": 0,
}



'''
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except serial.SerialException as e:
    print("Serial port error: ", e)
    exit(1)
'''



# fake serial for testing on laptop
class FakeSerial:
    def __init__(self):
        self._rx = deque()
        self._is_open = True

    @property
    def in_waiting(self):
        return len(self._rx)

    def readline(self):
        if not self._rx:
            time.sleep(0.01)
            return b""
        return self._rx.popleft()

    def write(self, data: bytes):
        text = data.decode(errors="ignore").strip().lower()
        print(f"[fake serial wrote] {text}")
        if "pi_ready" in text:
            self._rx.append(b"rodger\n")

    def close(self):
        self._is_open = False

    @property
    def is_open(self):
        return self._is_open

# Use this fake serial instead of the real port
ser = FakeSerial()
# end of temp class

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

# ——————————————————
# Precharge State
# ——————————————————
PRECHARGE_TARGET = 0.90
pack_voltage = 0.0
ic_voltage = 0.0
state_flags.update({
    "precharge_active": 0, # 1 while precharge relay is on and charging DC
    "precharge_ok": 0 # 1 when the IC >= 90%
})

# ——————————————————————
# Interprets Serial Data
# ——————————————————————
def handle_serial_line(line):
    global handshake, pack_voltage, ic_voltage
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
            state_flags["status"] = int(value)
            update_state_label()

        elif key == "ts_active":
            state_flags["ts_active"] = int(value)
            update_state_label()

        elif key == "manual_reset_ok":
            state_flags["manual_reset_ok"] = int(value)
            update_state_label()

        elif key == "sd":
            active = int(value)
            sd_lbl.config(
                text=f"SD: {'Active' if active else 'Idle'}",
                fg="lime" if active else "white"
            )
            faults["SDCARD"] = 0 if active else 1
            update_fault_label()

        elif key.startswith("fault_"):
            fault_name = key.split("_", 1)[1].upper()
            if fault_name in faults:
                faults[fault_name] = int(value)
                update_fault_label()   
                update_state_label()   

        elif key == "brk":
            on = (value == 1)
            set_dot(brake_circle, "red" if on else "gray25")
            state_flags["brk"] = int(on)
            update_state_label()

        elif key == "gas":
            on = (value == 1)
            set_dot(gas_circle, "green" if on else "gray25")
            state_flags["gas"] = int(on)
            update_state_label()

        elif key == "ts_v":
            pack_voltage = float(value)

        elif key == "ic_v":
            ic_voltage = float(value)
            pre_ok = int(pack_voltage > 0.0 and ic_voltage >= PRECHARGE_TARGET * pack_voltage)
            state_flags["precharge_ok"] = pre_ok
            update_state_label()

        elif key == "precharge_active":
            state_flags["precharge_active"] = int(value)
            update_state_label()

        elif key == "precharge_ok":
            state_flags["precharge_ok"] = int(value)
            update_state_label()

    
    except Exception as e:
        print("Serial parse error:", e)


# ——————————————————
# Updates fault labels
# ——————————————————
def faults_active():
    return any(val == 1 for val in faults.values())
def update_fault_label():
    crit = [k for k in CRITICAL_KEYS if faults.get(k,0) == 1]
    nonc = [k for k in NONCRITICAL_KEYS if faults.get(k,0) == 1]

    if crit:
        fault_lbl.config(
            text=f"TRACTIVE SYSTEM SHUTDOWN — {', '.join(crit)}",
            fg="white", bg="red"
        )
    else:
        fault_lbl.config(text="", bg="black")

    noncrit_text = f"Warnings: {', '.join(nonc)}" if nonc else ""
    noncrit_lbl.config(text=noncrit_text)   

# ——————————————————
# Updates state labels
# ——————————————————
def update_state_label():
    if any_critical_active() and state_flags.get("ts_active",0) == 0:
        state_lbl.config(text="SHUTDOWN", fg="red")

    if state_flags.get("precharge_active",0) == 1 and state_flags.get("precharge_ok",0) == 0:
        state_lbl.config(text="PRECHARGING…", fg="yellow")
        return

    if state_flags.get("ts_active",0) == 0:
        state_lbl.config(text="TRACTIVE SYSTEM OFF", fg="white")
        return

    if state_flags.get("status",0) == 0:
        state_lbl.config(text="Ready to Drive", fg="yellow")
    else:
        state_lbl.config(text="Enabled", fg="lime")
        

# ——————————————————
# RTD State
# ——————————————————
def rtd_ready_now():
    crit_ok = all(faults[k] == 0 for k in CRITICAL_KEYS)
    return crit_ok and state_flags.get("precharge_ok",0) == 1

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
bar_w_max = 645
bar_canvas = tk.Canvas(inner_frame, bg="gray20", highlightthickness=0)
bar_canvas.place(x=70, y=20, width=bar_w_max, height=bar_h)

# —————————————————
# Gauges underneath
# —————————————————
font_14 = ("Mono 91", 14)
font_20 = ("Mono 91", 20)
font_22 = ("Mono 91", 22)
font_26 = ("Mono 91", 26)
font_36 = ("Mono 91", 36)

# ——————————————————
# Display of Gas and Break
# ——————————————————
gas_circle = tk.Canvas(inner_frame, width=50, height=50, bg="black", highlightthickness=0)
gas_circle.place(x= 80 + bar_w_max, y=15) 

brake_circle = tk.Canvas(inner_frame, width=50, height=50, bg="black", highlightthickness=0)
brake_circle.place(x= 3, y=15)
def set_dot(canvas, color):
    canvas.delete("all")
    canvas.create_oval(5,5,45,45, fill=color, width = 0)

set_dot(gas_circle, "gray25")
set_dot(brake_circle, "gray25")

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

acc_temp_lbl = tk.Label(inner_frame, text="", font=font_14, fg="white", bg="black")
acc_temp_lbl.place(x=30, y=265)

noncrit_lbl = tk.Label(inner_frame, text="", font=("Mono 91", 16), fg="yellow", bg="black")
noncrit_lbl.place(x=30, y=300)

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

sd_lbl = tk.Label(inner_frame, text="SD: -", font=font_14, fg="white", bg="black")
sd_lbl.place(x= 500, y= 235)

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

# —————————————————————
# Fault banner at bottom center
# —————————————————————
fault_lbl = tk.Label(
    inner_frame,
    text="",  
    font=("Mono 91", 28, "bold"),
    fg="white",
    bg="black"
)
# Place the fault label at the center 
FAULT_Y = SCREEN_H // 2 
FAULT_X = SCREEN_W // 2  
fault_lbl.place(x=FAULT_X - 10, y=FAULT_Y - 20, anchor="center")

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


# ————————————————
# simulator in replacement of teensy
# ————————————————
t0 = time.time()
PH_FAULTS, PH_PRECHARGE, PH_READY, PH_DRIVE = 0, 1, 2, 3
phase = PH_FAULTS
phase_start = time.time()

SIM_INTERVAL_MS    = 150     
TIME_SPEED         = 0.6     
ACCEL_PER_SEC      = 300.0   # rpm/s when gas
BRAKE_DECEL_PER_SEC= 600.0   # rpm/s when brake
DRAG_PER_SEC       = 120.0   # rpm/s natural coast down
sim_rpm = 0.0

# --- helpers to drive faults from the simulator ---
def set_fault(name, on):
    handle_serial_line(f"fault_{name.lower()}={1 if on else 0}\n")

def clear_all_faults():
    for k in faults.keys():
        handle_serial_line(f"fault_{k.lower()}=0\n")
# --------------------------------------------------

def sim_tick():
    global phase, phase_start, sim_rpm

    # --- time bases ---
    real_t = time.time() - t0
    t  = real_t * TIME_SPEED
    dt = time.time() - phase_start

    # --- pedals (never both) ---
    gas = 1 if int(t * 1.0) % 2 == 0 else 0
    brk = 1 if int(t * 0.6) % 2 == 0 else 0
    if gas and brk:
        brk = 0
    handle_serial_line(f"gas={gas}\n")
    handle_serial_line(f"brk={brk}\n")

    # --- simulate internal rpm state ---
    loop_dt = SIM_INTERVAL_MS / 1000.0
    if brk:
        sim_rpm -= BRAKE_DECEL_PER_SEC * loop_dt
    elif gas:
        sim_rpm += ACCEL_PER_SEC * loop_dt
    else:
        sim_rpm -= DRAG_PER_SEC * loop_dt
    sim_rpm = max(0.0, min(float(MAX_RPM), sim_rpm))

    can_drive = (
        state_flags.get("status", 0) == 1 and
        state_flags.get("ts_active", 0) == 1 and
        not any(faults[k] == 1 for k in CRITICAL_KEYS)
    )
    ui_rpm  = int(sim_rpm) if can_drive else 0
    ui_pwr  = 800.0 * (ui_rpm / MAX_RPM) ** 1.3 if can_drive else 0.0
    handle_serial_line(f"mtr_s={ui_rpm}\n")
    handle_serial_line(f"pwr={ui_pwr:.2f}\n")

    if phase == PH_FAULTS:
        handle_serial_line("status=0\n")
        handle_serial_line("ts_active=0\n")
        handle_serial_line("sd=0\n") 

        # criticals ON
        handle_serial_line("fault_imd=1\n")
        handle_serial_line("fault_bms=1\n")

        # some bad readings
        handle_serial_line("acc_v=12.0\n")
        handle_serial_line("min_v=0.95\n")
        handle_serial_line("max_v=4.20\n")
        handle_serial_line("acc_t=95.0\n")
        handle_serial_line("mtr_t=105.0\n")
        handle_serial_line("cnt_t=110.0\n")
        handle_serial_line("cool_t=95.0\n")

        if dt > 5.0:
            handle_serial_line("fault_imd=0\n")
            handle_serial_line("fault_bms=0\n")
            phase = PH_PRECHARGE
            phase_start = time.time()

    elif phase == PH_PRECHARGE:
        handle_serial_line("status=0\n")
        handle_serial_line("ts_active=0\n")
        handle_serial_line("sd=0\n")         
        handle_serial_line("precharge_active=1\n")

        pack_v = 300.0
        ic_v   = min(pack_v, pack_v * (1 - math.exp(-dt / 1.5)))
        handle_serial_line(f"ts_v={pack_v}\n")
        handle_serial_line(f"ic_v={ic_v}\n")
        pre_ok = int(ic_v >= PRECHARGE_TARGET * pack_v)
        handle_serial_line(f"precharge_ok={pre_ok}\n")

        handle_serial_line("acc_v=15.5\n")
        handle_serial_line("min_v=3.200\n")
        handle_serial_line("max_v=4.100\n")
        handle_serial_line("acc_t=35.0\n")
        handle_serial_line("mtr_t=45.0\n")
        handle_serial_line("cnt_t=40.0\n")
        handle_serial_line("cool_t=30.0\n")

        if pre_ok and dt > 4.0:
            handle_serial_line("precharge_active=0\n")
            handle_serial_line("ts_active=1\n")
            phase = PH_READY
            phase_start = time.time()

    elif phase == PH_READY:
        handle_serial_line("status=0\n")
        handle_serial_line("ts_active=1\n")
        handle_serial_line("sd=0\n")          
        handle_serial_line("manual_reset_ok=1\n")

        handle_serial_line("acc_v=15.5\n")
        handle_serial_line("min_v=3.200\n")
        handle_serial_line("max_v=4.100\n")
        handle_serial_line("acc_t=35.0\n")
        handle_serial_line("mtr_t=45.0\n")
        handle_serial_line("cnt_t=40.0\n")
        handle_serial_line("cool_t=30.0\n")

        rtd_ready = (state_flags.get("precharge_ok", 0) == 1 and
                     not any(faults[k] == 1 for k in CRITICAL_KEYS))
        if rtd_ready and dt > 5.0:
            phase = PH_DRIVE
            phase_start = time.time()

    elif phase == PH_DRIVE:
        handle_serial_line("status=1\n")
        handle_serial_line("ts_active=1\n")
        handle_serial_line("sd=0\n")         

    root.after(SIM_INTERVAL_MS, sim_tick)



root.after(1200, sim_tick)

#end of simulator


root.mainloop()
