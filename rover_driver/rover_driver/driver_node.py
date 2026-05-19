#sudo chmod 666 /dev/ttyUSB0 --> USB bağlanması için terminale yazılması gereken izin kodu

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from .roboclaw_3 import Roboclaw
import time

class RoverDriver(Node):
    def __init__(self):
        super().__init__('rover_driver_node')

        # --- AYARLAR ---
        self.declare_parameter('port_name', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 115200)

        self.port     = self.get_parameter('port_name').get_parameter_value().string_value
        self.baudrate = self.get_parameter('baud_rate').get_parameter_value().integer_value
        
        # SÜRÜCÜ ADRESLERI
        self.ADDR_128 = 0x80  
        self.ADDR_129 = 0x81 
        self.ADDR_130 = 0x82  

        self.get_logger().info(f"Port: {self.port} | Baud: {self.baudrate}")
        self.connect_roboclaw()

        self.subscription = self.create_subscription(
            Float32MultiArray,
            'motor_commands',
            self.listener_callback,
            10)

        # İndeks Haritası: 0:M1, 1:M2, 2:M3, 3:M4, 4:M5, 5:Gripper
        self.targets = [0.0] * 6
        self.currents = [0.0] * 6
        self.RAMP_STEP = 2000.0
        self.last_msg_time = time.time()
        self.TIMEOUT_SEC = 0.5

        self.timer = self.create_timer(0.1, self.control_loop)
        self.get_logger().info("Driver Started (3 Controllers Aktif)")

    def connect_roboclaw(self):
        try:
            if hasattr(self, 'rc'):
                if hasattr(self.rc, '_port') and self.rc._port is not None:
                    if self.rc._port.is_open:
                        self.rc._port.close()
            time.sleep(0.5)
            self.rc = Roboclaw(self.port, self.baudrate)
            if self.rc.Open():
                self.get_logger().info("✅ Roboclaw CONNECTED/RECONNECTED!")
                return True
            else:
                self.get_logger().error("❌ Connection Failed! (Kabloyu kontrol et)")
                return False
        except Exception as e:
            self.get_logger().error(f"❌ Connection Error: {e}")
            return False

    def listener_callback(self, msg):
        # Mesajın uzunluğu 6 ise al, değilse hata fırlatmasını önle
        if len(msg.data) == 6:
            for i in range(6):
                self.targets[i] = msg.data[i]
            self.last_msg_time = time.time()
        else:
            self.get_logger().warn(f"Geçersiz mesaj boyutu: {len(msg.data)}")
            return

    def control_loop(self):
        elapsed_time = time.time() - self.last_msg_time
        if elapsed_time > self.TIMEOUT_SEC:
            self.targets = [0.0] * 6

        # --- RAMPALAMA (0'dan 5'e kadar tüm motorlar için) ---
        for i in range(6):
            target = self.targets[i]
            current = self.currents[i]
            error = target - current
            
            if abs(error) < self.RAMP_STEP:
                self.currents[i] = target
            else:
                if error > 0: self.currents[i] += self.RAMP_STEP
                else: self.currents[i] -= self.RAMP_STEP

        try:
            ROBOCLAW_MAX = 32767
            
            # Değerleri güvenli sınırlara çek (0:M1, 1:M2, 2:M3, 3:M4, 4:M5, 5:Gripper)
            v_m1 = max(min(int(self.currents[0]), ROBOCLAW_MAX), -ROBOCLAW_MAX)
            v_m2 = max(min(int(self.currents[1]), ROBOCLAW_MAX), -ROBOCLAW_MAX)
            v_m3 = max(min(int(self.currents[2]), ROBOCLAW_MAX), -ROBOCLAW_MAX)
            v_m4 = max(min(int(self.currents[3]), ROBOCLAW_MAX), -ROBOCLAW_MAX)
            v_m5 = max(min(int(self.currents[4]), ROBOCLAW_MAX), -ROBOCLAW_MAX)
            v_grip = max(min(int(self.currents[5]), ROBOCLAW_MAX), -ROBOCLAW_MAX)
            
            # --- BAĞLANTI HARİTASI ---
            # Roboclaw 1: adres 128 -> Motor1: M1 | Motor2: Gripper
            self.rc.DutyM1M2(self.ADDR_128, v_m1, v_grip)
            time.sleep(0.01) 

            # Roboclaw 2: adres 129 -> Motor1: M2 | Motor2: M3
            self.rc.DutyM1M2(self.ADDR_129, v_m2, v_m3)
            time.sleep(0.01)

            # Roboclaw 3: adres 130 -> Motor1: M4 | Motor2: M5
            self.rc.DutyM1M2(self.ADDR_130, v_m4, v_m5)

        except Exception as e:
            self.get_logger().error(f"⚠️ USB ERROR: {e}. Trying to Reconnect...")
            self.connect_roboclaw()

    def stop_all(self):
        try:
            self.rc.DutyM1M2(self.ADDR_128, 0, 0)
            time.sleep(0.02)
            self.rc.DutyM1M2(self.ADDR_129, 0, 0)
            time.sleep(0.02)
            self.rc.DutyM1M2(self.ADDR_130, 0, 0)
        except:
            pass

def main(args=None):
    rclpy.init(args=args)
    node = RoverDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.stop_all()
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()