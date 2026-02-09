# import os
# from ament_index_python.packages import get_package_share_directory
# import xacro
# from launch import LaunchDescription
# from launch.actions import DeclareLaunchArgument, LogInfo
import os
from ament_index_python.packages import get_package_share_directory
import xacro
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue
from launch.substitutions import Command


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    enable_joint_state_publisher = LaunchConfiguration('enable_joint_state_publisher')

    pkg_path = get_package_share_directory('Articubot_CT')
    xacro_file = os.path.join(pkg_path, 'description', 'robot.urdf.xacro')

    # 使用 Command 来加载 URDF
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]),
        value_type=str
    )

    params = {
        'robot_description': robot_description,
        'use_sim_time': use_sim_time
    }

    # robot_state_publisher
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[params],
        name='robot_state_publisher'
    )

    # joint_state_publisher（优先 GUI，否则 headless）
    try:
        get_package_share_directory('joint_state_publisher_gui')
        joint_state_publisher_node = Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
            condition=IfCondition(enable_joint_state_publisher)
        )
    except Exception:
        LogInfo(msg="使用 headless joint_state_publisher 作为回退")
        joint_state_publisher_node = Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            arguments=['--use-fixed-joints'],
            condition=IfCondition(enable_joint_state_publisher)
        )

    # RViz2
    rviz_config_file = os.path.join(pkg_path, 'config', 'view_bot.rviz')
    if os.path.exists(rviz_config_file):
        rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_file],
            parameters=[{'use_sim_time': use_sim_time}]
        )
    else:
        rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}]
        )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true', description='Use simulation time if true'),
        DeclareLaunchArgument('enable_joint_state_publisher', default_value='false', description='Enable joint_state_publisher (false by default when using gz_joint_state_bridge)'),
        LogInfo(msg="Starting robot_state_publisher..."),
        node_robot_state_publisher,
        joint_state_publisher_node,
        rviz_node,
        LogInfo(msg="等待节点启动..."),
        ExecuteProcess(cmd=['sleep', '2'], output='screen')
    ])
