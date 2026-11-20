from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='articubot_one',
            executable='rplidar_serial_publisher.py',
            name='rplidar_serial_publisher',
            output='screen',
            parameters=[{
                'port': '/dev/rlidar_gpio',
                'frame_id': 'laser_frame',
                'range_min': 0.15,
                'baudrate': 115200,
                'scan_frequency': 10.0,   # la tasa real se ajusta sola
            }],
        )
    ])