"""
rover_control.launch.py
========================
ÇALIŞTIRILDIĞI YER : Operatör bilgisayarı (laptop/masaüstü)
BAŞLATTIKLARI      : joy_node  +  rover_teleop (mod1 veya mod2)

Neden ayrı launch?
  Aynı ağda başka bir paket de joy kullandığı için /joy topic'i çakışır.
  Bu launch, joy_node'u /robotarm_joy namespace'ine remap'leyerek
  sadece bu kolun teleop'unun kendi joystick'ini dinlemesini sağlar.

─────────────────────────────────────────────────────────────────────
  NORMAL BAŞLATMA:
    ros2 launch rover_control rover_control.launch.py

  MOD SEÇİMİ:
    ros2 launch rover_control rover_control.launch.py teleop_mode:=1
    ros2 launch rover_control rover_control.launch.py teleop_mode:=2

  KALİBRASYON (joystick merkezdeyken):
    ros2 launch rover_control rover_control.launch.py calibrate:=true

  ÖRNEKLER:
    ros2 launch rover_control rover_control.launch.py teleop_mode:=1 calibrate:=true
    ros2 launch rover_control rover_control.launch.py motor_speed:=20000.0
    ros2 launch rover_control rover_control.launch.py teleop_mode:=2 motor_speed:=15000.0 calibrate:=true

  JOY CİHAZ NUMARASI (iki joy varsa hangisinin bu kol için olduğunu belirt):
    ros2 launch rover_control rover_control.launch.py joy_device:=/dev/input/js1
─────────────────────────────────────────────────────────────────────

TOPIC AKIŞI:
  [joy_node]  --/robotarm_joy-->  [rover_teleop_node]  --/motor_komutlari-->  (driver bunu dinler)

NOT: driver_node ayrı bir makinede (Jetson) rover_driver.launch.py ile başlatılır.
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
        # /joy  →  /robotarm_joy  olarak remap edilir.
        # Böylece aynı bilgisayarda çalışan diğer joy paketleriyle çakışmaz.
        # ------------------------------------------------------------------
        Node(
            package='joy',
            executable='joy_node',
            name='robotarm_joy_node',           # node adı da benzersiz
            parameters=[{
                'device_name':     joy_dev,
                'deadzone':        0.05,
                'autorepeat_rate': 20.0,
            }],
            remappings=[
                ('joy', 'robotarm_joy'),         # /joy → /robotarm_joy
            ],
            output='screen',
        ),

        # ------------------------------------------------------------------
        # rover_teleop (mod1 veya mod2)
        # Teleop da /joy yerine /robotarm_joy'u dinleyecek şekilde remap edilir.
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
            remappings=[
                ('joy', 'robotarm_joy'),         # /joy → /robotarm_joy
            ],
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
            description='Joystick cihaz adi veya yolu (orn: /dev/input/js1). Bos: ilk bulunan.',
        ),

        OpaqueFunction(function=launch_setup),
    ])