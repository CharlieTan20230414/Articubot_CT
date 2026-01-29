#!/usr/bin/env python3
"""
检查TF树和里程计话题的脚本
"""
import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener
from nav_msgs.msg import Odometry

class TFChecker(Node):
    def __init__(self):
        super().__init__('tf_checker')

        # 创建TF缓冲区和监听器
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # 订阅里程计话题
        self.odom_sub = self.create_subscription(
            Odometry,
            '/model/Articubot_CT/odometry',
            self.odom_callback,
            10
        )

        # 创建定时器，定期检查TF
        self.timer = self.create_timer(1.0, self.check_tf)

        self.odom_received = False

    def odom_callback(self, msg):
        if not self.odom_received:
            self.get_logger().info('✅ 收到里程计消息')
            self.get_logger().info(f'   帧ID: {msg.header.frame_id}')
            self.get_logger().info(f'   子帧ID: {msg.child_frame_id}')
            self.get_logger().info(f'   位置: x={msg.pose.pose.position.x:.3f}, y={msg.pose.pose.position.y:.3f}, z={msg.pose.pose.position.z:.3f}')
            self.odom_received = True

    def check_tf(self):
        try:
            # 尝试获取odom到base_link的变换
            transform = self.tf_buffer.lookup_transform(
                'odom',
                'base_link',
                rclpy.time.Time()
            )
            self.get_logger().info('✅ TF变换 odom -> base_link 存在')
            self.get_logger().info(f'   平移: x={transform.transform.translation.x:.3f}, y={transform.transform.translation.y:.3f}, z={transform.transform.translation.z:.3f}')
        except Exception as e:
            self.get_logger().warn(f'❌ 无法获取TF变换: {e}')

        if not self.odom_received:
            self.get_logger().warn('❌ 未收到里程计消息')

def main(args=None):
    rclpy.init(args=args)
    tf_checker = TFChecker()

    try:
        rclpy.spin(tf_checker)
    except KeyboardInterrupt:
        pass

    tf_checker.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
