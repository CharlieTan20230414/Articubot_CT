# 调试指南

## 问题解决

### odom_to_tf节点没有运行

**问题原因：**
1. Python脚本没有正确安装到ROS2包中
2. launch文件中使用了ExecuteProcess而不是Node来启动脚本
3. 脚本缺少use_sim_time参数支持

**解决方案：**
1. 修改了setup.py中的entry_points配置，使用正确的模块路径
2. 修改了spawn_Articubot_CT.launch.py，使用ROS2的Node方式启动odom_to_tf
3. 修改了odom_to_tf.py，添加了use_sim_time参数支持

### Gazebo插件TF冲突

**问题原因：**
Gazebo的差速驱动插件配置了`publish_odom_tf=true`，会自动发布odom到base_link的TF变换，与我们的odom_to_tf节点产生冲突。

**解决方案：**
1. 修改了gazebo_control.xacro，禁用Gazebo的TF发布（`publish_odom_tf=false`）
2. 修改了odom_topic为`/model/Articubot_CT/odometry`，与bridge配置一致
3. 只使用odom_to_tf节点发布TF变换，避免冲突

### 重新构建和运行

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

### 验证节点运行

1. 使用check_tf脚本检查TF和里程计：
```bash
ros2 run Articubot_CT check_tf
```
这个脚本会自动检查：
- 是否收到里程计消息
- TF变换 odom -> base_link 是否存在

2. 检查节点列表：
```bash
ros2 node list
```
应该看到以下节点：
- /robot_state_publisher
- /odom_to_tf
- /ros_gz_bridge

3. 检查TF树：
```bash
ros2 run tf2_tools view_frames
```
应该看到完整的TF树，包括odom -> base_link

4. 检查里程计话题：
```bash
ros2 topic echo /model/Articubot_CT/odometry
```

5. 检查TF变换：
```bash
ros2 run tf2_ros tf2_echo odom base_link
```

### 常见问题

1. 如果odom_to_tf节点仍然没有运行：
   - 检查Python脚本权限：`chmod +x scripts/odom_to_tf.py`
   - 检查Python脚本是否有语法错误：`python3 scripts/odom_to_tf.py`
   - 检查ROS2环境是否正确source

2. 如果TF树仍然不完整：
   - 检查bridge节点是否正常运行
   - 检查里程计话题是否发布数据
   - 检查odom_to_tf节点的日志输出

3. 如果RViz2中Fixed Frame无法选择odom：
   - 等待几秒让TF树建立
   - 刷新RViz2的Fixed Frame下拉列表
   - 检查odom_to_tf节点是否正常广播TF变换
