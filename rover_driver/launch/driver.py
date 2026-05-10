"""
rover_driver.launch.py
=======================
ÇALIŞTIRILDIĞI YER : Jetson (robot üzerindeki bilgisayar)
BAŞLATTIKLARI      : rover_driver_node (Roboclaw motor sürücüsü)

Bu launch yalnızca driver_node'u ayağa kaldırır.
joy ve teleop bilgisayarda çalışır; bu node sadece
/motor_komutlari topic'ini dinleyerek motorları sürer.

─────────────────────────────────────────────────────────────────────
  BAŞLATMA:
    ros2 launch rover_driver rover_driver.launch.py

  NOT: USB izni için önce çalıştır:
    sudo chmod 666 /dev/ttyUSB0
─────────────────────────────────────────────────────────────────────

TOPIC AKIŞI:
  [rover_teleop_node (bilgisayar)]  --/motor_komutlari-->  [rover_driver_node (Jetson)]
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # ------------------------------------------------------------------
        # rover_driver_node
        # Roboclaw üzerinden motorları sürer.
        # /motor_komutlari topic'ini dinler, başka bir şey başlatmaz.
        # ------------------------------------------------------------------
        Node(
            package='rover_driver',
            executable='driver_node',
            name='rover_driver_node',
            output='screen',
        ),
    ])