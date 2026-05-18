import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Float32MultiArray

# ==============================================================================
#  MOD 2 — İki-Slot Motor Seçim Mantığı + Proportional Kalibrasyon
# ==============================================================================
#  Logitech Attack 3 - Eksen & Buton Haritası
# ==============================================================================
#  axes[0]  : X ekseni  (sola = +1.0,  sağa  = -1.0)  → Slot-B
#  axes[1]  : Y ekseni  (ileri = +1.0, geri  = -1.0)  → Slot-A
#
#  buttons[0]  : Tetik (Trigger)  ← KULLANILMIYOR
#  buttons[1]  : Buton 2          ← M1      
#  buttons[2]  : Buton 3          ← M2       
#  buttons[3]  : Buton 4          ← M3      
#  buttons[4]  : Buton 5          ← M4       
#  buttons[5]  : Buton 6          ← M5       
#  buttons[6]  : Buton 7          ← Gripper 
# ==============================================================================

BUTON_MOTOR_MAP = {
    1: 0,   # Buton 2 -> M1 
    2: 1,   # Buton 3 -> M2
    3: 2,   # Buton 4 -> M3 
    4: 3,   # Buton 5 -> M4 
    5: 4,   # Buton 6 -> M5 
    6: 5,   # Buton 7 -> Gripper 
}

MOTOR_ISIM = {0: "M1", 1: "M2", 2: "M3", 3: "M4", 4: "M5", 5: "Gripper"}

DEFAULT_CAL_PATH = os.path.expanduser("~/.ros/joystick_cal.txt")

class RoverTeleopMod2(Node):
    def __init__(self):
        super().__init__('rover_teleop_node')

        self.declare_parameter('motor_speed',      30000.0)
        self.declare_parameter('axis_deadzone',    0.15)
        self.declare_parameter('calibration_file', DEFAULT_CAL_PATH)
        self.declare_parameter('calibrate',        False)

        self.last_commands = [0.0] * 6
        self.prev_buttons  = []
        self.axis_offsets: list[float] = []
        self.cal_done      = False

        self.slot_a: int | None = None
        self.slot_b: int | None = None

        if not self.get_parameter('calibrate').value:
            self._load_calibration()
        else:
            self.get_logger().info("Kalibrasyon modu ACIK — joystick'i merkeze getirin.")

        self.subscription = self.create_subscription(Joy, 'joy', self.joy_callback, 10)
        self.publisher_ = self.create_publisher(Float32MultiArray, 'motor_komutlari', 10)
        self.timer = self.create_timer(0.1, self.timer_callback)

    def _load_calibration(self):
        cal_file = self.get_parameter('calibration_file').value
        if not os.path.isfile(cal_file):
            self.axis_offsets = []
            return
        try:
            with open(cal_file, 'r') as f:
                parts = f.read().strip().split()
            self.axis_offsets = [float(v) for v in parts]
        except Exception as e:
            self.axis_offsets = []

    def _save_calibration(self, axes: list[float]):
        cal_file = self.get_parameter('calibration_file').value
        os.makedirs(os.path.dirname(cal_file), exist_ok=True)
        try:
            with open(cal_file, 'w') as f:
                f.write(" ".join(f"{v:.6f}" for v in axes))
            self.axis_offsets = list(axes)
        except Exception as e:
            self.get_logger().error(f"Kalibrasyon kaydedilemedi: {e}")

    def get_axis(self, msg: Joy, index: int) -> float:
        if index >= len(msg.axes):
            return 0.0
        raw    = msg.axes[index]
        offset = self.axis_offsets[index] if index < len(self.axis_offsets) else 0.0
        return max(min(raw - offset, 1.0), -1.0)

    def _log_slots(self):
        a_isim = MOTOR_ISIM.get(self.slot_a, "---") if self.slot_a is not None else "---"
        b_isim = MOTOR_ISIM.get(self.slot_b, "---") if self.slot_b is not None else "---"
        self.get_logger().info(f"Slot-A (ileri/geri): {a_isim} | Slot-B (sag/sol): {b_isim}")

    def joy_callback(self, msg: Joy):
        if self.get_parameter('calibrate').value and not self.cal_done:
            self._save_calibration(list(msg.axes))
            self.cal_done = True
            self.prev_buttons = [0] * len(msg.buttons)
            return

        if not self.axis_offsets:
            self.axis_offsets = [0.0] * len(msg.axes)

        motor_speed     = self.get_parameter('motor_speed').value
        deadzone        = self.get_parameter('axis_deadzone').value
        current_buttons = list(msg.buttons)

        if not self.prev_buttons:
            self.prev_buttons = [0] * len(current_buttons)

        # Buton Kontrolü
        for btn_idx, data_idx in BUTON_MOTOR_MAP.items():
            if btn_idx >= len(current_buttons):
                continue
            prev = self.prev_buttons[btn_idx] if btn_idx < len(self.prev_buttons) else 0
            curr = current_buttons[btn_idx]

            if curr != 1 or prev != 0:
                continue

            if self.slot_a == data_idx:
                self.slot_a = None
            elif self.slot_b == data_idx:
                self.slot_b = None
            elif self.slot_a is None:
                self.slot_a = data_idx
            elif self.slot_b is None:
                self.slot_b = data_idx
            else:
                self.get_logger().warn("Her iki slot dolu! Once birini bosaltin.")
            
            self._log_slots()

        self.prev_buttons = current_buttons

        emirler = Float32MultiArray()
        emirler.data = [0.0] * 6

        # Oransal (Proportional) Hız Haritalama [-1, 1] -> [-motor_speed, motor_speed]
        if self.slot_a is not None:
            axis_a = self.get_axis(msg, 1)
            if abs(axis_a) > deadzone:
                emirler.data[self.slot_a] = axis_a * motor_speed

        if self.slot_b is not None:
            axis_b = self.get_axis(msg, 0)
            if abs(axis_b) > deadzone:
                emirler.data[self.slot_b] = axis_b * motor_speed

        self.last_commands = list(emirler.data)
        self.publisher_.publish(emirler)

    def timer_callback(self):
        msg = Float32MultiArray()
        msg.data = self.last_commands
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = RoverTeleopMod2()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()