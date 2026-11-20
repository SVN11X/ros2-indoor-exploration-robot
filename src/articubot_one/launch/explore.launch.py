from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    bringup_dir = get_package_share_directory('articubot_one')
    
    # Declarar el argumento use_sim_time
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    explore_params_file = LaunchConfiguration('explore_params_file')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true'),

        DeclareLaunchArgument(
            'explore_params_file',
            default_value=os.path.join(bringup_dir, 'config', 'explore.yaml'),
            description='Full path to explore params file'
        ),

        Node(
            package='explore_lite',
            executable='explore',
            name='explore_server',
            output='screen',
            parameters=[
                explore_params_file,
                {'use_sim_time': use_sim_time}  # <--- ¡IMPORTANTE!
            ]
        ),
    ])
