import os
import xacro
from launch import LaunchDescription
from launch.actions import TimerAction, LogInfo, ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_articubot_ct_path = get_package_share_directory('Articubot_CT')
    model_path = os.path.join(pkg_articubot_ct_path, 'description', 'robot.urdf.xacro')

    # 使用xacro处理模型文件，得到URDF字符串
    xacro_file = xacro.process_file(model_path)
    robot_description_content = xacro_file.toxml()

    world_path = os.path.join(pkg_articubot_ct_path, 'worlds', 'empty.world')

    # 启动Gazebo
    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', world_path],
        output='screen',
        emulate_tty=True
    )

    # 时钟桥接
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # 生成模型的节点（使用 -string 直接传入URDF）
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'Articubot_CT', '-string', robot_description_content, '-x', '0.0', '-y', '0.0', '-z', '0.5'],
        output='screen'
    )

    # 桥接配置
    bridge_config = [
        '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
        '/model/Articubot_CT/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry',
    ]

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=bridge_config,
        output='screen',
        parameters=[{'use_sim_time': True}],
        remappings=[('/model/Articubot_CT/joint_state', '/joint_states')]
    )

    # 里程计转TF节点
    odom_to_tf = Node(
        package='Articubot_CT',
        executable='odom_to_tf',
        name='odom_to_tf',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'odom_topic': '/model/Articubot_CT/odometry',
            'odom_frame': 'odom',
            'base_frame': 'base_link'
        }]
    )

    gz_joint_state_bridge = Node(
        package='Articubot_CT',
        executable='gz_joint_state_bridge',
        name='gz_joint_state_bridge',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    gz_joint_state_bridge_delayed = TimerAction(
        period=3.5,  # 在 bridge 之后启动
        actions=[gz_joint_state_bridge],
    )

    # 延迟启动（确保Gazebo就绪）
    clock_bridge_delayed = TimerAction(period=1.0, actions=[clock_bridge])
    spawn_entity_delayed = TimerAction(period=2.0, actions=[spawn_entity])
    bridge_delayed = TimerAction(period=3.0, actions=[bridge])
    odom_to_tf_delayed = TimerAction(period=4.0, actions=[odom_to_tf])

    log_info = LogInfo(msg="Starting Articubot_CT simulation with proper timing...")

    return LaunchDescription([
        log_info,
        gazebo,
        clock_bridge_delayed,
        spawn_entity_delayed,
        bridge_delayed,
        odom_to_tf_delayed,
        gz_joint_state_bridge_delayed 
    ])