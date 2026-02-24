#!/usr/bin/env python3
import importlib
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState

class GZJointStateBridge(Node):
    def __init__(self):
        super().__init__('gz_joint_state_bridge')
        self.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])

        self.pub = self.create_publisher(JointState, '/joint_states', 10)
        self.topic = '/model/Articubot_CT/joint_state'

        # 直接导入 gz.msgs10.joint_state_pb2 模块
        try:
            mod = importlib.import_module('gz.msgs10.joint_state_pb2')
            msg_cls = getattr(mod, 'JointState')
            self.sub = self.create_subscription(msg_cls, self.topic, self.cb, 10)
            self.get_logger().info(f"✅ Subscribed to {self.topic} with gz.msgs10.joint_state_pb2.JointState")
        except Exception as e:
            self.get_logger().error(f"❌ Failed to subscribe: {e}")
            raise

    def cb(self, msg):
        names = []
        positions = []
        velocities = []
        efforts = []

        try:
            if hasattr(msg, 'name') and hasattr(msg, 'position'):
                names = list(msg.name)
                positions = list(msg.position)
                if hasattr(msg, 'velocity'):
                    velocities = list(msg.velocity)
                if hasattr(msg, 'effort'):
                    efforts = list(msg.effort)
            else:
                self.get_logger().debug(f"Unknown joint message type: {type(msg)}")
                return
        except Exception as e:
            self.get_logger().warning(f"Error extracting joint data: {e}")
            return

        if len(names) == 0:
            self.get_logger().debug("No joint names extracted")
            return

        out = JointState()
        out.header.stamp = self.get_clock().now().to_msg()
        out.name = names
        out.position = positions
        out.velocity = velocities if velocities else [0.0] * len(names)
        out.effort = efforts if efforts else [0.0] * len(names)

        self.pub.publish(out)
        self.get_logger().debug(f"Published /joint_states with {len(names)} joints")

def main():
    rclpy.init()
    node = GZJointStateBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()