import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Float32MultiArray


# ==============================================================================
#  MOD 2 — İki-Slot Motor Seçim Mantığı + Terminal Kalibrasyonu
# ==============================================================================
#  Logitech Attack 3 - Eksen & Buton Haritası
# ==============================================================================
#  axes[0]  : X ekseni  (sola = +1.0,  sağa  = -1.0)  → Slot-B
#  axes[1]  : Y ekseni  (ileri = +1.0, geri  = -1.0)  → Slot-A
#  axes[2]  : Gaz kolu  (kullanılmıyor)
#
#  buttons[0]  : Tetik (Trigger)  ← BOŞ (ileride kullanılacak)
#  buttons[1]  : Buton 2          ← BOŞ (ileride kullanılacak)
#  buttons[2]  : Buton 3          ← M1 seçimi
#  buttons[3]  : Buton 4          ← M2 seçimi
#  buttons[4]  : Buton 5          ← M3 seçimi
#  buttons[5]  : Buton 6          ← M4 seçimi
#  buttons[6]  : Buton 7          ← M5 seçimi
#  buttons[7]  : Buton 8          ← M6 seçimi
#  buttons[8]  : Buton 9          ← BOŞ (Gripper ileride)
#
#  İki Slot Mantığı:
#  ┌─────────┬────────────────────────────────────────────┐
#  │ Slot-A  │ axes[1] ileri/geri  — ilk seçilen motor    │
#  │ Slot-B  │ axes[0] sağa/sola   — ikinci seçilen motor │
#  └─────────┴────────────────────────────────────────────┘
#  Aynı butona tekrar basınca o motorun slotu boşalır.
#  İki slot doluyken yeni motor seçmeye çalışınca uyarı verilir.
#
#  KALİBRASYON:
#    Launch sırasında calibrate:=true → ilk joy mesajı offset olarak kaydedilir
#    Sonraki başlatmalarda calibrate:=false (varsayılan) → dosyadan yüklenir
#
#  data[] İndeks Haritası (driver_node ile birebir aynı):
#  0:Boş  1:Boş  2:M1  3:M2  4:M3  5:M4  6:M5  7:M6  8:Gripper(kapalı)
# ==============================================================================

BUTON_MOTOR_MAP = {
    2: 2,   # Buton 3 → M1
    3: 3,   # Buton 4 → M2
    4: 4,   # Buton 5 → M3
    5: 5,   # Buton 6 → M4
    6: 6,   # Buton 7 → M5
    7: 7,   # Buton 8 → M6
}

MOTOR_ISIM = {2: "M1", 3: "M2", 4: "M3", 5: "M4", 6: "M5", 7: "M6"}

DEFAULT_CAL_PATH = os.path.expanduser("~/.ros/joystick_cal.txt")


class RoverTeleopMod2(Node):
    def __init__(self):
        super().__init__('rover_teleop_node')

        # ------------------------------------------------------------------
        # PARAMETRELER
        # ------------------------------------------------------------------
        self.declare_parameter('motor_speed',      30000.0)
        self.declare_parameter('axis_deadzone',    0.15)
        self.declare_parameter('calibration_file', DEFAULT_CAL_PATH)
        # True ise ilk joy mesajı offset olarak kaydedilir
        self.declare_parameter('calibrate',        False)

        # ------------------------------------------------------------------
        # DURUM
        # ------------------------------------------------------------------
        self.last_commands = [0.0] * 9
        self.prev_buttons  = []
        self.axis_offsets: list[float] = []
        self.cal_done      = False

        self.slot_a: int | None = None
        self.slot_b: int | None = None

        # ------------------------------------------------------------------
        # KALİBRASYON DOSYASINI OKU (calibrate=false ise)
        # ------------------------------------------------------------------
        if not self.get_parameter('calibrate').value:
            self._load_calibration()
        else:
            self.get_logger().info(
                "Kalibrasyon modu ACIK — joystick'i merkeze getirin.\n"
                "  Ilk joy mesaji geldiginde offset kaydedilecek...")

        # ------------------------------------------------------------------
        # ROS BAĞLANTILARI
        # ------------------------------------------------------------------
        self.subscription = self.create_subscription(
            Joy, 'joy', self.joy_callback, 10)

        self.publisher_ = self.create_publisher(
            Float32MultiArray, 'motor_komutlari', 10)

        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info(
            "MOD 2 HAZIR!\n"
            "  Buton 3-8 → motor sec (1. basis Slot-A, 2. basis Slot-B)\n"
            "  Ayni butona tekrar bas  → o slotu bosalt\n"
            "  Trigger & Buton 2 → BOS")

    # ======================================================================
    #  KALİBRASYON
    # ======================================================================

    def _load_calibration(self):
        cal_file = self.get_parameter('calibration_file').value
        if not os.path.isfile(cal_file):
            self.get_logger().warn(
                f"Kalibrasyon dosyasi bulunamadi: {cal_file}\n"
                "  Sifir offset ile devam ediliyor.\n"
                "  Kalibrasyon icin: ros2 launch ... calibrate:=true")
            self.axis_offsets = []
            return
        try:
            with open(cal_file, 'r') as f:
                parts = f.read().strip().split()
            self.axis_offsets = [float(v) for v in parts]
            offset_str = ", ".join(f"{v:.3f}" for v in self.axis_offsets)
            self.get_logger().info(f"Kalibrasyon yuklendi: [{offset_str}]")
        except Exception as e:
            self.get_logger().error(f"Kalibrasyon okunamadi: {e}")
            self.axis_offsets = []

    def _save_calibration(self, axes: list[float]):
        cal_file = self.get_parameter('calibration_file').value
        os.makedirs(os.path.dirname(cal_file), exist_ok=True)
        try:
            with open(cal_file, 'w') as f:
                f.write(" ".join(f"{v:.6f}" for v in axes))
            self.axis_offsets = list(axes)
            offset_str = ", ".join(f"{v:.3f}" for v in self.axis_offsets)
            self.get_logger().info(
                f"Kalibrasyon kaydedildi -> {cal_file}\n  [{offset_str}]")
        except Exception as e:
            self.get_logger().error(f"Kalibrasyon kaydedilemedi: {e}")

    # ======================================================================
    #  EKSEN OKUMA
    # ======================================================================

    def get_axis(self, msg: Joy, index: int) -> float:
        if index >= len(msg.axes):
            return 0.0
        raw    = msg.axes[index]
        offset = self.axis_offsets[index] if index < len(self.axis_offsets) else 0.0
        return max(min(raw - offset, 1.0), -1.0)

    # ======================================================================
    #  SLOT DURUM LOGU
    # ======================================================================

    def _log_slots(self):
        a_isim = MOTOR_ISIM.get(self.slot_a, "---") if self.slot_a is not None else "---"
        b_isim = MOTOR_ISIM.get(self.slot_b, "---") if self.slot_b is not None else "---"
        self.get_logger().info(
            f"  Slot-A (ileri/geri): {a_isim}   |   Slot-B (sag/sol): {b_isim}")

    # ======================================================================
    #  JOY CALLBACK
    # ======================================================================

    def joy_callback(self, msg: Joy):
        # ------------------------------------------------------------------
        # KALİBRASYON — calibrate=true ise ilk mesajda yap, sonra normal çalış
        # ------------------------------------------------------------------
        if self.get_parameter('calibrate').value and not self.cal_done:
            self._save_calibration(list(msg.axes))
            self.cal_done = True
            self.prev_buttons = [0] * len(msg.buttons)
            self.get_logger().info("Kalibrasyon tamamlandi. Normal operasyona gecildi.")
            return

        # ------------------------------------------------------------------
        # Offset listesi boşsa sıfırla doldur
        # ------------------------------------------------------------------
        if not self.axis_offsets:
            self.axis_offsets = [0.0] * len(msg.axes)

        motor_speed     = self.get_parameter('motor_speed').value
        deadzone        = self.get_parameter('axis_deadzone').value
        current_buttons = list(msg.buttons)

        if not self.prev_buttons:
            self.prev_buttons = [0] * len(current_buttons)

        # ------------------------------------------------------------------
        # MOTOR SEÇİM BUTONLARI — rising edge toggle
        # ------------------------------------------------------------------
        for btn_idx, data_idx in BUTON_MOTOR_MAP.items():
            if btn_idx >= len(current_buttons):
                continue
            prev = self.prev_buttons[btn_idx] if btn_idx < len(self.prev_buttons) else 0
            curr = current_buttons[btn_idx]

            if curr != 1 or prev != 0:
                continue

            if self.slot_a == data_idx:
                self.slot_a = None
                self.get_logger().info(f"{MOTOR_ISIM[data_idx]} Slot-A'dan cikarildi.")
                self._log_slots()
            elif self.slot_b == data_idx:
                self.slot_b = None
                self.get_logger().info(f"{MOTOR_ISIM[data_idx]} Slot-B'den cikarildi.")
                self._log_slots()
            elif self.slot_a is None:
                self.slot_a = data_idx
                self.get_logger().info(f"{MOTOR_ISIM[data_idx]} -> Slot-A (ileri/geri)")
                self._log_slots()
            elif self.slot_b is None:
                self.slot_b = data_idx
                self.get_logger().info(f"{MOTOR_ISIM[data_idx]} -> Slot-B (sag/sol)")
                self._log_slots()
            else:
                a_isim = MOTOR_ISIM.get(self.slot_a, "?")
                b_isim = MOTOR_ISIM.get(self.slot_b, "?")
                self.get_logger().warn(
                    f"Her iki slot dolu! (A={a_isim}, B={b_isim})\n"
                    f"  Once bir motorun butonuna basarak slotu bosalt.")

        self.prev_buttons = current_buttons

        # ------------------------------------------------------------------
        # MOTORLARI SÜPÜR
        # ------------------------------------------------------------------
        emirler = Float32MultiArray()
        emirler.data = [0.0] * 9

        if self.slot_a is not None:
            axis_a = self.get_axis(msg, 1)
            if axis_a > deadzone:
                emirler.data[self.slot_a] = motor_speed
            elif axis_a < -deadzone:
                emirler.data[self.slot_a] = -motor_speed

        if self.slot_b is not None:
            axis_b = self.get_axis(msg, 0)
            if axis_b > deadzone:
                emirler.data[self.slot_b] = motor_speed
            elif axis_b < -deadzone:
                emirler.data[self.slot_b] = -motor_speed

        self.last_commands = list(emirler.data)
        self.publisher_.publish(emirler)

    # ======================================================================
    #  TIMER
    # ======================================================================

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
