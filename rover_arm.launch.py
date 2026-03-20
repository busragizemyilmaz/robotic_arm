"""
rover_arm.launch.py
====================
Tüm rover kol düğümlerini tek seferde başlatır:
  1. joy_node          — joystick sürücüsü
  2. rover_teleop      — operatör arayüzü (Mod 1 veya Mod 2)
  3. rover_driver_node — Roboclaw motor sürücüsü

─────────────────────────────────────────────────────────
  NORMAL BAŞLATMA (mevcut kalibrasyon dosyasını yükler):
    ros2 launch rover_control rover_arm.launch.py

  KALİBRASYONLU BAŞLATMA (joystick merkezdeyken):
    ros2 launch rover_control rover_arm.launch.py calibrate:=true

  MOD SEÇİMİ:
    ros2 launch rover_control rover_arm.launch.py teleop_mode:=1
    ros2 launch rover_control rover_arm.launch.py teleop_mode:=2

  ÖRNEKLER:
    ros2 launch rover_control rover_arm.launch.py teleop_mode:=1 calibrate:=true
    ros2 launch rover_control rover_arm.launch.py motor_speed:=20000.0
    ros2 launch rover_control rover_arm.launch.py teleop_mode:=2 motor_speed:=15000.0 calibrate:=true
─────────────────────────────────────────────────────────
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    teleop_mode = context.perform_substitution(LaunchConfiguration('teleop_mode'))
    calibrate   = LaunchConfiguration('calibrate')
    motor_speed = LaunchConfiguration('motor_speed')
    axis_dz     = LaunchConfiguration('axis_deadzone')
    cal_file    = LaunchConfiguration('calibration_file')
    joy_dev     = LaunchConfiguration('joy_device')

    teleop_executable = 'mod1' if teleop_mode == '1' else 'mod2'

    nodes = [
        # ------------------------------------------------------------------
        # joy_node
        # ------------------------------------------------------------------
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{
                'device_name':    joy_dev,
                'deadzone':       0.05,
                'autorepeat_rate': 20.0,
            }],
            output='screen',
        ),

        # ------------------------------------------------------------------
        # rover_teleop (mod1 veya mod2)
        # ------------------------------------------------------------------
        Node(
            package='rover_control',
            executable=teleop_executable,
            name='rover_teleop_node',
            parameters=[{
                'motor_speed':      motor_speed,
                'axis_deadzone':    axis_dz,
                'calibration_file': cal_file,
                'calibrate':        calibrate,
            }],
            output='screen',
        ),

        # ------------------------------------------------------------------
        # rover_driver_node
        # sudo chmod 666 /dev/ttyUSB0
        # ------------------------------------------------------------------
        Node(
            package='rover_driver',
            executable='driver_node',
            name='rover_driver_node',
            output='screen',
        ),
    ]

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'teleop_mode',
            default_value='2',
            description='1=Mod1 (cift-buton)  2=Mod2 (iki-slot)',
        ),
        DeclareLaunchArgument(
            'calibrate',
            default_value='false',
            description='true: ilk joy mesajini kalibrasyon offseti olarak kaydet',
        ),
        DeclareLaunchArgument(
            'motor_speed',
            default_value='30000.0',
            description='Maksimum motor hiz degeri (0-32767)',
        ),
        DeclareLaunchArgument(
            'axis_deadzone',
            default_value='0.15',
            description='Joystick merkez olu bolgesi (0.0-1.0)',
        ),
        DeclareLaunchArgument(
            'calibration_file',
            default_value='~/.ros/joystick_cal.txt',
            description='Kalibrasyon dosyasinin tam yolu',
        ),
        DeclareLaunchArgument(
            'joy_device',
            default_value='',
            description='Joystick cihaz adi (bos birakinca ilk bulunan kullanilir)',
        ),

        OpaqueFunction(function=launch_setup),
    ])
