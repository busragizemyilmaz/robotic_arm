import os
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Float32MultiArray


# ==============================================================================
#  MOD 1 — Eski Çift-Buton Mantığı + Terminal Kalibrasyonu
# ==============================================================================
#  Logitech Attack 3 - Eksen & Buton Haritası
# ==============================================================================
#  axes[0]  : X ekseni  (sola = +1.0,  sağa = -1.0)  → M1
#  axes[1]  : Y ekseni  (ileri = +1.0, geri = -1.0)  → (Gripper — kapalı)
#
#  buttons[0]  : Tetik (Trigger)  ← BOŞ (ileride kullanılacak)
#  buttons[1]  : Buton 2          ← M2 İleri
#  buttons[2]  : Buton 3          ← M2 Geri
#  buttons[3]  : Buton 4          ← M3 İleri
#  buttons[4]  : Buton 5          ← M3 Geri
#  buttons[5]  : Buton 6          ← M4 İleri
#  buttons[6]  : Buton 7          ← M4 Geri
#  buttons[7]  : Buton 8          ← M5 İleri
#  buttons[8]  : Buton 9          ← M5 Geri
#  buttons[9]  : Buton 10         ← M6 İleri
#  buttons[10] : Buton 11         ← M6 Geri
#
#  KALİBRASYON:
#    Launch sırasında calibrate:=true → ilk joy mesajı offset olarak kaydedilir
#    Sonraki başlatmalarda calibrate:=false (varsayılan) → dosyadan yüklenir
#
#  data[] İndeks Haritası (driver_node ile birebir aynı):
#  0:Boş  1:Boş  2:M1  3:M2  4:M3  5:M4  6:M5  7:M6  8:Gripper(kapalı)
# ==============================================================================

DEFAULT_CAL_PATH = os.path.expanduser("~/.ros/joystick_cal.txt")


class RoverTeleopMod1(Node):
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
        self.last_commands   = [0.0] * 9
        self.axis_offsets: list[float] = []
        self.cal_done        = False   # ilk mesaj kalibrasyonu yapıldı mı

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
            "MOD 1 HAZIR!\n"
            "  axes[0] sag/sol → M1\n"
            "  Buton ciftleri (2-11) ile M2-M6 kontrol\n"
            "  Trigger (Buton 1) → BOŞ")

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
    #  JOY CALLBACK
    # ======================================================================

    def joy_callback(self, msg: Joy):
        # ------------------------------------------------------------------
        # KALİBRASYON — calibrate=true ise ilk mesajda yap, sonra normal çalış
        # ------------------------------------------------------------------
        if self.get_parameter('calibrate').value and not self.cal_done:
            self._save_calibration(list(msg.axes))
            self.cal_done = True
            self.get_logger().info("Kalibrasyon tamamlandi. Normal operasyona gecildi.")
            return   # Bu frame'i komuta dönüştürme

        # ------------------------------------------------------------------
        # Offset listesi boşsa (dosya yoktu) axis sayısı kadar sıfırla doldur
        # ------------------------------------------------------------------
        if not self.axis_offsets:
            self.axis_offsets = [0.0] * len(msg.axes)

        motor_speed     = self.get_parameter('motor_speed').value
        deadzone        = self.get_parameter('axis_deadzone').value
        current_buttons = list(msg.buttons)

        # ------------------------------------------------------------------
        # KOMUTLARI HESAPLA
        # ------------------------------------------------------------------
        emirler = Float32MultiArray()
        emirler.data = [0.0] * 9

        # --- EKSENLER ---

        # M1 (axes[0] sağ/sol)
        ax0 = self.get_axis(msg, 0)
        if ax0 > deadzone:
            emirler.data[2] = motor_speed
        elif ax0 < -deadzone:
            emirler.data[2] = -motor_speed

        # Gripper (data[8]) — kapalı

        # --- BUTONLAR (çift, basılı tutunca sürekli çalışır) ---

        # M2 (buttons[1] / buttons[2])
        if len(current_buttons) > 1 and current_buttons[1] == 1:
            emirler.data[3] = motor_speed
        elif len(current_buttons) > 2 and current_buttons[2] == 1:
            emirler.data[3] = -motor_speed

        # M3 (buttons[3] / buttons[4])
        if len(current_buttons) > 3 and current_buttons[3] == 1:
            emirler.data[4] = motor_speed
        elif len(current_buttons) > 4 and current_buttons[4] == 1:
            emirler.data[4] = -motor_speed

        # M4 (buttons[5] / buttons[6])
        if len(current_buttons) > 5 and current_buttons[5] == 1:
            emirler.data[5] = motor_speed
        elif len(current_buttons) > 6 and current_buttons[6] == 1:
            emirler.data[5] = -motor_speed

        # M5 (buttons[7] / buttons[8])
        if len(current_buttons) > 7 and current_buttons[7] == 1:
            emirler.data[6] = motor_speed
        elif len(current_buttons) > 8 and current_buttons[8] == 1:
            emirler.data[6] = -motor_speed

        # M6 (buttons[9] / buttons[10])
        if len(current_buttons) > 9 and current_buttons[9] == 1:
            emirler.data[7] = motor_speed
        elif len(current_buttons) > 10 and current_buttons[10] == 1:
            emirler.data[7] = -motor_speed

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
    node = RoverTeleopMod1()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
