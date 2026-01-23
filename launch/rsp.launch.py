# import os
# from ament_index_python.packages import get_package_share_directory
# import xacro
# from launch import LaunchDescription
# from launch.actions import DeclareLaunchArgument, LogInfo
# from launch.substitutions import LaunchConfiguration
# from launch_ros.actions import Node

# def generate_launch_description():
#     use_sim_time = LaunchConfiguration('use_sim_time')

#     pkg_path = get_package_share_directory('Articubot_CT')
#     xacro_file = os.path.join(pkg_path, 'description', 'robot.urdf.xacro')

#     try:
#         robot_description_config = xacro.process_file(xacro_file).toxml()
#         print(f"✅ URDF 加载成功: {len(robot_description_config)} 字符")
#     except Exception as e:
#         print(f"❌ URDF 加载失败: {e}")
#         raise

#     params = {'robot_description': robot_description_config, 'use_sim_time': use_sim_time}

#     node_robot_state_publisher = Node(
#         package='robot_state_publisher',
#         executable='robot_state_publisher',
#         output='screen',
#         parameters=[params]
#     )

#     rviz_node = Node(
#         package='rviz2',
#         executable='rviz2',
#         name='rviz2',
#         output='screen',
#         arguments=['-d', os.path.join(pkg_path, 'rviz', 'robot.rviz')]
#     )



#     joint_state_publisher_node = Node(
#         package='joint_state_publisher',
#         executable='joint_state_publisher',
#         name='joint_state_publisher',
#         output='screen',
#         arguments=['--use-fixed-joints']
#     )

#     return LaunchDescription([
#         DeclareLaunchArgument('use_sim_time', default_value='false', description='If true, use simulation time'),
#         LogInfo(msg="Starting robot_state_publisher..."),
#         node_robot_state_publisher,
#         rviz_node,
#         joint_state_publisher_node
#     ])
import os
from ament_index_python.packages import get_package_share_directory
import xacro
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue
from launch.substitutions import Command, LaunchConfiguration

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    
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
    
    # 1. robot_state_publisher
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[params],
        name='robot_state_publisher'
    )
    
    # 2. 尝试使用 joint_state_publisher_gui，如果失败则使用替代方案
    try:
        # 检查包是否存在
        print("检查 joint_state_publisher_gui 包是否存在...")
        get_package_share_directory('joint_state_publisher_gui')
        joint_state_publisher_node = Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen'
        )
    except:
        # 使用命令行工具发布静态关节状态
        LogInfo(msg="使用静态关节状态发布器")
        joint_state_publisher_node = ExecuteProcess(
            cmd=[
                'ros2', 'topic', 'pub', '-r', '10', 
                '/joint_states', 'sensor_msgs/msg/JointState',
                '{\"header\": {\"stamp\": {\"sec\": 0, \"nanosec\": 0}, \"frame_id\": \"world\"}, \"name\": [\"joint1\", \"joint2\"], \"position\": [0.0, 0.0], \"velocity\": [0.0, 0.0], \"effort\": [0.0, 0.0]}'
            ],
            output='screen',
            name='static_joint_state_publisher'
        )
    
    # 3. RViz2
    rviz_config_file = os.path.join(pkg_path, 'rviz', 'display.rviz')
    
    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(rviz_config_file):
        rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}]
        )
    else:
        rviz_node = Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_file],
            parameters=[{'use_sim_time': use_sim_time}]
        )
    
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation time if true'
        ),
        
        node_robot_state_publisher,
        joint_state_publisher_node,
        rviz_node,
        
        # 添加一个延迟启动来确保所有节点都准备好
        LogInfo(msg="等待节点启动..."),
        ExecuteProcess(
            cmd=['sleep', '2'],
            output='screen'
        )
    ])