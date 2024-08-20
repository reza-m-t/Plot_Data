import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import threading
import openpyxl
from tkinter import Tk, Entry, Button, Label, StringVar, filedialog, Frame, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import time

# تنظیمات اولیه برای صف‌های داده
temperature_data = deque(maxlen=100)
voltage_data = deque(maxlen=100)
current_data = deque(maxlen=100)
power_data = deque(maxlen=100)
time_data = deque(maxlen=100)

ser = None  # تعریف متغیر جهانی برای ارتباط سریال
connected = False  # متغیر برای بررسی وضعیت اتصال
lock = threading.Lock()
time_counter = 0  # شمارنده زمان برای پیگیری داده‌ها
workbook = None
worksheet = None

# ایجاد پنجره اصلی Tkinter
root = Tk()
root.title("Serial Data Plotter")  # عنوان پنجره اصلی

# متغیر Tkinter برای ذخیره مسیر فایل
save_path_var = StringVar()

def browse_save_path():
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
    if file_path:
        save_path_var.set(file_path)
        initialize_excel()
        start_data_acquisition()

def initialize_excel():
    global workbook, worksheet
    if save_path_var.get():
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Serial Data"
        worksheet.append(["Time", "Temperature (°C)", "Voltage (V)", "Current (A)", "Power (W)"])
        workbook.save(save_path_var.get())

def save_to_excel(time_counter, temperature, voltage, current, power):
    global workbook, worksheet
    if workbook and worksheet:
        worksheet.append([time_counter, temperature, voltage, current, power])
        workbook.save(save_path_var.get())

def parse_and_plot_data(line):
    global time_counter
    try:
        # جدا کردن مقادیر از هم
        parts = line.split('-')
        if len(parts) != 4:
            print(f"Warning: Incorrect number of parts: expected 4, got {len(parts)}")
            return
        
        # تبدیل رشته‌ها به مقادیر عددی
        try:
            temperature, voltage, current, power = map(float, parts)
        except ValueError as e:
            print(f"Error: {e}")
            return

        with lock:
            # اضافه کردن مقادیر به صف‌ها
            temperature_data.append(temperature)
            voltage_data.append(voltage)
            current_data.append(current)
            power_data.append(power)
            time_data.append(time_counter)

            # ذخیره در اکسل
            threading.Thread(target=save_to_excel, args=(time_counter, temperature, voltage, current, power)).start()

        time_counter += 1  # افزایش شمارنده زمان

    except ValueError as e:
        print(f"Error: {e}")

def read_serial_data():
    global ser, connected
    while connected:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                parse_and_plot_data(line)
            else:
                # بررسی برای قطع ارتباط
                if not ser.is_open:
                    handle_disconnection()
        except (serial.SerialException, ValueError) as e:
            print(f"Error: {e}")
            handle_disconnection()

def handle_disconnection():
    global connected
    connected = False
    show_disconnection_message()
    auto_connect_serial()

def show_disconnection_message():
    messagebox.showwarning("Disconnected", "Connection lost. Attempting to reconnect...")

def update_plot(i):
    global connected
    if connected and len(time_data) > 0:  # بررسی اینکه داده‌ها خالی نیستند
        with lock:
            # پاک کردن نمودارها
            ax1.clear()
            ax2.clear()
            ax3.clear()
            ax4.clear()

            # رسم داده‌ها با استایل بهتر
            ax1.plot(time_data, temperature_data, label="Temperature (°C)", color='red', linewidth=1.5)
            ax2.plot(time_data, voltage_data, label="Voltage (V)", color='blue', linewidth=1.5)
            ax3.plot(time_data, current_data, label="Current (A)", color='green', linewidth=1.5)
            ax4.plot(time_data, power_data, label="Power (W)", color='purple', linewidth=1.5)

            # افزودن عناوین و برچسب‌ها
            ax1.set_title('Temperature Over Time')
            ax1.set_ylabel('Temperature (°C)')
            ax1.grid(True)

            ax2.set_title('Voltage Over Time')
            ax2.set_ylabel('Voltage (V)')
            ax2.grid(True)

            ax3.set_title('Current Over Time')
            ax3.set_ylabel('Current (A)')
            ax3.set_xlabel('Time (s)')
            ax3.grid(True)

            ax4.set_title('Power Over Time')
            ax4.set_ylabel('Power (W)')
            ax4.set_xlabel('Time (s)')
            ax4.grid(True)

            # تنظیم محدودیت‌های محور Y برای حفظ وضوح نمودار
            ax1.set_ylim([min(temperature_data) - 10, max(temperature_data) + 10])
            ax2.set_ylim([min(voltage_data) - 10, max(voltage_data) + 10])
            ax3.set_ylim([min(current_data) - 1, max(current_data) + 1])
            ax4.set_ylim([min(power_data) - 10, max(power_data) + 10])

            # افزودن عناوین و شبکه‌بندی (grid)
            ax1.legend(loc="upper right")
            ax2.legend(loc="upper right")
            ax3.legend(loc="upper right")
            ax4.legend(loc="upper right")

def auto_connect_serial():
    global ser, connected
    if ser and ser.is_open:
        print(f"Already connected to {ser.port}")
        return
    
    ports = serial.tools.list_ports.comports()
    for port in ports:
        try:
            ser = serial.Serial(port.device, 9600, timeout=2)
            print(f"Connected to {port.device}")
            connected = True
            threading.Thread(target=read_serial_data, daemon=True).start()
            return
        except serial.SerialException:
            continue
    
    print("Disconnected")
    connected = False
    time.sleep(2)

def start_data_acquisition():
    initialize_excel()
    auto_connect_serial()

def on_closing():
    global connected
    if connected:
        connected = False
        if ser:
            ser.close()
    root.destroy()

# تنظیمات نمودار matplotlib
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle('Real-Time Serial Data Visualization', fontsize=16)

ani = animation.FuncAnimation(fig, update_plot, interval=100, cache_frame_data=False)

# افزودن فیلد ورودی و دکمه به پنجره
label = Label(root, text="Select Excel Save Path:")
label.pack(side='top')

entry = Entry(root, textvariable=save_path_var, width=50)
entry.pack(side='top', fill='x')

button_browse = Button(root, text="Browse...", command=browse_save_path)
button_browse.pack(side='top')

# Frame برای نمایش نمودار
plot_frame = Frame(root)
plot_frame.pack(fill='both', expand=True)

canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.draw()
canvas.get_tk_widget().pack(fill='both', expand=True)

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()  # اجرای پنجره Tkinter
