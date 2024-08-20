import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import time
import threading

# صف‌های داده با محدودیت اندازه 100
temperature_data = deque(maxlen=100)
voltage_data = deque(maxlen=100)
current_data = deque(maxlen=100)
power_data = deque(maxlen=100)
time_data = deque(maxlen=100)

ser = None  # تعریف متغیر جهانی برای ارتباط سریال
connected = False  # متغیر برای بررسی وضعیت اتصال
lock = threading.Lock()
time_counter = 0  # شمارنده زمان برای پیگیری داده‌ها

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

        time_counter += 1  # افزایش شمارنده زمان

    except ValueError as e:
        print(f"Error: {e}")

def read_serial_data():
    global ser, connected
    while connected:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                parse_and_plot_data(line)
        except (serial.SerialException, ValueError) as e:
            print(f"Error: {e}")
            connected = False
            if ser:
                ser.close()
            auto_connect_serial()

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

# تنظیمات نمودار matplotlib
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle('Real-Time Serial Data Visualization', fontsize=16)

ani = animation.FuncAnimation(fig, update_plot, interval=100)

auto_connect_serial()

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.show()
