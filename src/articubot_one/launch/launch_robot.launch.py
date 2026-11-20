import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node

def generate_launch_description():
    package_name='articubot_one'

    pkg_path = os.path.join(get_package_share_directory(package_name))
    xacro_file = os.path.join(pkg_path,'description','robot.urdf.xacro')
    
    # Procesar Xacro
    robot_description = Command(['xacro ', xacro_file, ' use_ros2_control:=true'])

    # 1. Robot State Publisher
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(pkg_path,'launch','rsp.launch.py')]),
        launch_arguments={'use_sim_time': 'false', 'use_ros2_control': 'true'}.items()
    )

    # 2. Twist Mux
    #twist_mux_params = os.path.join(pkg_path,'config','twist_mux.yaml')
    #twist_mux = Node(
    #    package="twist_mux",
    #    executable="twist_mux",
    #    parameters=[twist_mux_params],
    #    remappings=[('/cmd_vel_out','/diff_cont/cmd_vel_unstamped')]
    #)

    # 3. Controller Manager
    controller_params_file = os.path.join(pkg_path,'config','my_controllers.yaml')
    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[{'robot_description': robot_description},
                    controller_params_file]
    )

    # Spawners diferidos
    delayed_controller_manager = TimerAction(period=3.0, actions=[controller_manager])
    
    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner.py",
        arguments=["diff_cont"]
    )

    joint_broad_spawner = Node(
        package="controller_manager",
        executable="spawner.py",
        arguments=["joint_broad"]
    )

    return LaunchDescription([
        rsp,
        delayed_controller_manager,
        diff_drive_spawner,
        joint_broad_spawner
    ])
