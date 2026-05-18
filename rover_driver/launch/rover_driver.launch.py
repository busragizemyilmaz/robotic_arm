"""
rover_driver.launch.py
=======================
ÇALIŞTIRILDIĞI YER : Jetson (robot üzerindeki bilgisayar)
BAŞLATTIKLARI      : rover_driver_node (Roboclaw motor sürücüsü)

─────────────────────────────────────────────────────────────────────
  BAŞLATMA (varsayılan port):
    ros2 launch rover_driver rover_driver.launch.py

  PORT BELİRTME (iki USB varsa hangisi Roboclaw'a bağlı?):
    ros2 launch rover_driver rover_driver.launch.py port_name:=/dev/ttyUSB0
    ros2 launch rover_driver rover_driver.launch.py port_name:=/dev/ttyUSB1

  NOT: USB izni için önce çalıştır:
    sudo chmod 666 /dev/ttyUSB0   (veya ttyUSB1)
─────────────────────────────────────────────────────────────────────

TOPIC AKIŞI:
  [rover_teleop_node (bilgisayar)]  --/motor_komutlari-->  [rover_driver_node (Jetson)]
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    port_name = LaunchConfiguration('port_name')
    baud_rate = LaunchConfiguration('baud_rate')

    return LaunchDescription([
        DeclareLaunchArgument(
            'port_name',
            default_value='/dev/ttyUSB0',
            description='Roboclaw USB port (orn: /dev/ttyUSB0 veya /dev/ttyUSB1)',
        ),
        DeclareLaunchArgument(
            'baud_rate',
            default_value='115200',
            description='Roboclaw baud rate',
        ),
        Node(
            package='rover_driver',
            executable='driver_node',
            name='rover_driver_node',
            output='screen',
            parameters=[
                {'port_name': port_name},
                {'baud_rate': baud_rate},
            ],
        ),
    ])
