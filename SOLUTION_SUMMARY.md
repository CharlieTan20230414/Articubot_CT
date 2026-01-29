# 解决方案总结

## 问题分析

1. **odom_to_tf节点没有运行**：节点列表中没有`/odom_to_tf`节点
2. **有两个robot_state_publisher节点**：这可能导致冲突
3. **TF树仍然不完整**：缺少odom帧
4. **RViz2中Fixed Frame无法选择odom**：因为没有odom帧被发布
5. **模型在RViz2中正常显示但不能跟随移动**：因为TF树不完整

## 根本原因

1. **odom_to_tf节点启动方式不正确**：使用ExecuteProcess直接运行Python脚本，而不是通过ROS2的节点系统
2. **Python脚本路径配置错误**：setup.py中的entry_points配置使用了错误的模块路径
3. **Gazebo插件TF冲突**：Gazebo的差速驱动插件配置了`publish_odom_tf=true`，与odom_to_tf节点产生冲突
4. **缺少use_sim_time参数**：odom_to_tf节点没有正确处理仿真时间

## 解决方案

### 1. 修改spawn_Articubot_CT.launch.py

- 将odom_to_tf节点从ExecuteProcess改为Node方式启动
- 添加延迟启动，确保依赖节点已就绪
- 为robot_state_publisher节点添加use_sim_time参数
- 为bridge节点添加use_sim_time参数
- 修正bridge配置中的里程计话题桥接方向，从Ignition桥接到ROS2

### 2. 修改odom_to_tf.py

- 添加use_sim_time参数支持
- 根据use_sim_time参数选择使用消息时间戳或当前时间
- 添加节点启动日志

### 3. 修改setup.py

- 修正entry_points配置，使用正确的模块路径：`Articubot_CT.scripts.odom_to_tf:main`
- 添加check_tf脚本的入口点

### 4. 修改gazebo_control.xacro

- 禁用Gazebo的TF发布：`publish_odom_tf=false`
- 修改odom_topic为`/model/Articubot_CT/odometry`，与bridge配置一致

### 5. 创建check_tf.py脚本

- 自动检查TF变换和里程计话题
- 提供实时的系统状态反馈

## 下一步操作

1. 重新构建工作空间：
```bash
cd /home/tanjianan/dev_ws
colcon build --packages-select Articubot_CT
source install/setup.bash
```

2. 启动仿真：
```bash
ros2 launch Articubot_CT spawn_Articubot_CT.launch.py
```

3. 在另一个终端启动RViz2：
```bash
rviz2
```

4. 在RViz2中设置Fixed Frame为"odom"

5. 验证系统运行：
```bash
# 使用check_tf脚本检查TF和里程计
ros2 run Articubot_CT check_tf

# 检查节点列表
ros2 node list

# 检查TF树
ros2 run tf2_tools view_frames

# 检查里程计话题
ros2 topic echo /model/Articubot_CT/odometry

# 检查TF变换
ros2 run tf2_ros tf2_echo odom base_link
```

## 预期结果

1. odom_to_tf节点正常运行
2. TF树完整，包含odom -> base_link变换
3. RViz2中可以选择odom作为Fixed Frame
4. 机器人在RViz2中能够跟随移动
5. 只有一个robot_state_publisher节点运行

## 注意事项

1. 确保在启动仿真前已经source了工作空间的setup.bash
2. 如果遇到问题，请查看TROUBLESHOOTING.md文件
3. 如果odom_to_tf节点仍然没有运行，请检查Python脚本的权限和语法
4. 如果TF树仍然不完整，请检查bridge节点和里程计话题是否正常
