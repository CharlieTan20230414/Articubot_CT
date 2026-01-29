import os
import xacro
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, LogInfo
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from launch.actions import ExecuteProcess


def generate_launch_description():
    # 使用ROS2的包路径查找方式获取模型文件路径
    pkg_articubot_ct_path = get_package_share_directory('Articubot_CT')
    model_path = os.path.join(pkg_articubot_ct_path, 'description', 'robot.urdf.xacro')

    # 使用xacro处理模型文件
    xacro_file = xacro.process_file(model_path)
    robot_description_content = xacro_file.toxml()

    # robot_state_publisher节点，用于发布robot_description话题
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': True
        }]
    )

    # 获取世界文件路径
    world_path = os.path.join(pkg_articubot_ct_path, 'worlds', 'empty.world')

    # 启动Gazebo并加载世界文件
    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', world_path],
        output='screen',
        emulate_tty=True
    )
    
    # 添加一个节点来发布初始时钟消息，稳定仿真时钟
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    # 生成模型的节点
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'Articubot_CT', '-topic', 'robot_description', '-x', '0.0', '-y', '0.0', '-z', '0.5'],
        output='screen'
    )

    # 添加ROS 2与Gazebo之间的桥接节点
    bridge_config = [
        '/cmd_vel@geometry_msgs/msg/Twist@ignition.msgs.Twist',
        '/model/Articubot_CT/odometry@nav_msgs/msg/Odometry@ignition.msgs.Odometry',
        '/joint_states@sensor_msgs/msg/JointState@ignition.msgs.JointState',
    ]
    
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=bridge_config,
        output='screen',
        parameters=[{'use_sim_time': True}]
    )
    
    # 添加一个节点，用于将Gazebo的里程计信息转换为TF变换
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

    # 添加延迟，确保Gazebo完全启动
    from launch.actions import TimerAction
    
    # 延迟1秒后启动clock_bridge
    clock_bridge_delayed = TimerAction(
        period=1.0,
        actions=[clock_bridge],
    )

    # 延迟2秒后启动spawn_entity，确保Gazebo已经完全启动
    spawn_entity_delayed = TimerAction(
        period=2.0,
        actions=[spawn_entity],
    )

    # 延迟3秒后启动bridge，确保spawn_entity已经完成
    bridge_delayed = TimerAction(
        period=3.0,
        actions=[bridge],
    )

    # 延迟4秒后启动odom_to_tf，确保bridge已经建立
    odom_to_tf_delayed = TimerAction(
        period=4.0,
        actions=[odom_to_tf],
    )
    
    # 添加日志信息
    log_info = LogInfo(msg="Starting Articubot_CT simulation with proper timing...")
    
    return LaunchDescription([
        log_info,
        robot_state_publisher,
        gazebo,
        clock_bridge_delayed,
        spawn_entity_delayed,
        bridge_delayed,
        odom_to_tf_delayed,
    ])