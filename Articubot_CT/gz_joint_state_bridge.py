#!/usr/bin/env python3
import importlib
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.duration import Duration
from rclpy.time import Time
from sensor_msgs.msg import JointState
import threading


class GZJointStateBridge(Node):
    def __init__(self):
        super().__init__('gz_joint_state_bridge')

        self.declare_parameter('input_topic', '/world/default/model/Articubot_CT/joint_state')
        self.declare_parameter('alternate_input_topics', ['/model/Articubot_CT/joint_state', '/model/Articubot_CT/joint_states'])
        self.declare_parameter('output_topic', '/joint_states')
        self.declare_parameter('timeout_sec', 5.0)

        self.input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        self.alternate_input_topics = self.get_parameter('alternate_input_topics').get_parameter_value().string_array_value
        self.output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self.timeout_sec = self.get_parameter('timeout_sec').get_parameter_value().double_value

        self.pub = self.create_publisher(JointState, self.output_topic, 10)

        # Candidate ROS message types to try for the incoming Gazebo topic
        self.candidates = [
            'sensor_msgs.msg.JointState',
            'ignition_msgs.msg.JointState',
            'ros_gz_msgs.msg.JointState',
            'gz_msgs.msg.JointState',
            'gz.msgs.JointState',
            'ignition.msgs.JointState',
            'gazebo_msgs.msg.JointState',
        ]

        self.sub = None
        self.sub_msg_type = None
        self.msg_received_event = threading.Event()

        # Try subscribing to the configured topic and alternate topics
        topics_to_try = [self.input_topic] + list(self.alternate_input_topics)
        for topic in topics_to_try:
            if self.try_create_subscription(topic):
                self.get_logger().info(f"Subscribed to {topic} with message type {self.sub_msg_type}")
                break
        else:
            self.get_logger().warning('Could not subscribe to any expected Gazebo joint topic with tried message types')

        # If no messages arrive within timeout, log and keep trying in background
        self.create_timer(1.0, self._check_messages)

        # wheel odometry fallback parameters
        self.declare_parameter('wheel_radius', 0.05)
        self.declare_parameter('wheel_separation', 0.35)
        self.wheel_radius = self.get_parameter('wheel_radius').get_parameter_value().double_value
        self.wheel_separation = self.get_parameter('wheel_separation').get_parameter_value().double_value

        # state for odom integration fallback
        self.left_angle = 0.0
        self.right_angle = 0.0
        self._last_odom_time = None
        self._odom_sub = None

        # simulation clock readiness
        self.has_sim_time = False
        self._last_clock = None
        # subscribe to /clock to get simulation time directly
        try:
            from rosgraph_msgs.msg import Clock
            self._clock_sub = self.create_subscription(Clock, '/clock', self._clock_cb, 10)
        except Exception:
            self._clock_sub = None
        # timer to detect when /clock has begun publishing (non-zero)
        self.create_timer(0.5, self._check_clock_ready)

    def try_create_subscription(self, topic_name: str) -> bool:
        # Try each candidate message type to create a subscription and wait briefly for a message
        for candidate in self.candidates:
            mod_name, cls_name = candidate.rsplit('.', 1)
            try:
                mod = importlib.import_module(mod_name)
                msg_cls = getattr(mod, cls_name)
            except Exception:
                continue

            # create a temporary subscription
            try:
                if self.sub is not None:
                    self.destroy_subscription(self.sub)
                    self.sub = None

                self.sub_msg_type = candidate
                self.sub = self.create_subscription(msg_cls, topic_name, self._cb_factory(), 10)

                # wait for a short period to see if message arrives
                self.msg_received_event.clear()
                got = self.msg_received_event.wait(timeout=self.timeout_sec)
                if got:
                    # message was received; keep this subscription
                    return True
                else:
                    # no message; destroy and try next
                    self.destroy_subscription(self.sub)
                    self.sub = None
                    self.sub_msg_type = None
            except Exception as e:
                # failed to create subscription with this type
                self.get_logger().debug(f"Failed to subscribe to {topic_name} with {candidate}: {e}")
                self.sub = None
                self.sub_msg_type = None
                continue
        return False

    def _cb_factory(self):
        def cb(msg):
            # Called whenever a message is received on the Gazebo joint topic
            # Try to pluck out joint names and positions from whatever message structure exists
            names = []
            positions = []
            velocities = []
            efforts = []

            # Various possible fields
            try:
                if hasattr(msg, 'name') and hasattr(msg, 'position'):
                    names = list(msg.name)
                    positions = list(getattr(msg, 'position'))
                    # velocities/efforts may or may not exist
                    if hasattr(msg, 'velocity'):
                        velocities = list(getattr(msg, 'velocity'))
                    if hasattr(msg, 'effort'):
                        efforts = list(getattr(msg, 'effort'))
                elif hasattr(msg, 'joint_names') and hasattr(msg, 'joint_positions'):
                    names = list(getattr(msg, 'joint_names'))
                    positions = list(getattr(msg, 'joint_positions'))
                elif hasattr(msg, 'joints'):
                    # some messages have a repeated 'joints' field with subfields
                    try:
                        for j in msg.joints:
                            if hasattr(j, 'name'):
                                names.append(j.name)
                            if hasattr(j, 'position'):
                                positions.append(j.position)
                    except Exception:
                        pass
                else:
                    # fallback: try to stringify
                    self.get_logger().debug(f"Unknown joint message structure: {type(msg)}")
            except Exception as e:
                self.get_logger().warning(f"Error extracting joint data: {e}")

            if len(names) == 0:
                # no useful data
                return

            # build sensor_msgs/JointState
            out = JointState()
            # Prefer using node's simulation clock timestamp to avoid clock domain mismatches
            try:
                now = self.get_clock().now()
                if self.has_sim_time:
                    out.header.stamp = now.to_msg()
                else:
                    # if sim time not ready yet, fall back to incoming message stamp if present
                    if hasattr(msg, 'header') and getattr(msg.header, 'stamp', None) is not None:
                        out.header.stamp = msg.header.stamp
                    else:
                        out.header.stamp = now.to_msg()
            except Exception:
                out.header.stamp = self.get_clock().now().to_msg()

            out.name = names
            out.position = positions
            out.velocity = velocities if velocities else [0.0] * len(names)
            out.effort = efforts if efforts else [0.0] * len(names)

            # choose stamp: prefer incoming msg.header, but prefer /clock if available (sim time)
            if self._last_clock is not None:
                chosen_stamp = self._last_clock
                chosen_source = '/clock'
            elif hasattr(msg, 'header') and getattr(msg.header, 'stamp', None) is not None:
                chosen_stamp = msg.header.stamp
                chosen_source = 'msg.header'
            else:
                chosen_stamp = self.get_clock().now().to_msg()
                chosen_source = 'now'

            out.header.stamp = chosen_stamp
            # If the chosen stamp is 'now' (node's clock) but sim time not ready,
            # skip publishing to avoid wall-time timestamps that RViz will treat as old.
            if chosen_source == 'now' and not self.has_sim_time:
                self.get_logger().debug('Skipping publish: sim time not ready and stamp came from node now')
            else:
                self.pub.publish(out)
            self.get_logger().debug(f"Published /joint_states with stamp {out.header.stamp.sec}.{out.header.stamp.nanosec} (chosen from {chosen_source})")
            # signal that we've received one message for detection
            self.msg_received_event.set()

        return cb

    def _check_messages(self):
        # If we have no subscription, try to create one again
        if self.sub is None:
            topics_to_try = [self.input_topic] + list(self.alternate_input_topics)
            for topic in topics_to_try:
                if self.try_create_subscription(topic):
                    self.get_logger().info(f"Late-subscribed to {topic} with type {self.sub_msg_type}")
                    break

        # If still no subscription to joint state-like messages, subscribe to odometry as a fallback
        if self.sub is None and self._odom_sub is None:
            try:
                from nav_msgs.msg import Odometry
                self._odom_sub = self.create_subscription(Odometry, '/model/Articubot_CT/odometry', self._odom_cb, 50)
                self.get_logger().info('Subscribed to /model/Articubot_CT/odometry for wheel integration fallback')
            except Exception as e:
                self.get_logger().debug(f'Could not subscribe to odometry fallback: {e}')

    def _check_clock_ready(self):
        # Detect whether simulation clock (/clock) has started (non-zero)
        try:
            if self._last_clock is not None and not self.has_sim_time:
                self.has_sim_time = True
                self.get_logger().info('Detected simulation time via /clock subscription')
        except Exception:
            pass

    def _clock_cb(self, msg):
        try:
            self._last_clock = msg.clock
        except Exception:
            self._last_clock = None

    def _odom_cb(self, msg):
        # integrate wheel rotations from odometry when joint_states unavailable
        try:
            t = msg.header.stamp
            cur_time = Time(seconds=t.sec, nanoseconds=t.nanosec)
            if self._last_odom_time is None:
                self._last_odom_time = cur_time
                return

            dt = (cur_time - self._last_odom_time).nanoseconds * 1e-9
            if dt <= 0:
                return

            v = msg.twist.twist.linear.x
            omega = msg.twist.twist.angular.z

            # differential drive kinematics
            half_sep = self.wheel_separation / 2.0
            v_left = v - omega * half_sep
            v_right = v + omega * half_sep

            delta_left = (v_left * dt) / self.wheel_radius
            delta_right = (v_right * dt) / self.wheel_radius

            self.left_angle += delta_left
            self.right_angle += delta_right

            out = JointState()
            # Use node's simulation clock if ready, otherwise fall back to odom stamp
            try:
                if self._last_clock is not None:
                    out.header.stamp = self._last_clock
                else:
                    out.header.stamp = msg.header.stamp
            except Exception:
                out.header.stamp = self.get_clock().now().to_msg()
            out.name = ['left_wheel_joint', 'right_wheel_joint', 'caster_wheel_joint']
            out.position = [self.left_angle, self.right_angle, 0.0]
            out.velocity = []
            out.effort = []
            self.pub.publish(out)
            # detailed debug: show integration inputs and outputs
            self.get_logger().debug(
                f"ODEM-INT dt={dt:.6f}s v={v:.6e} omega={omega:.6e} v_left={v_left:.6e} v_right={v_right:.6e} "
                f"delta_l={delta_left:.6e} delta_r={delta_right:.6e} left={self.left_angle:.6e} right={self.right_angle:.6e} "
                f"stamp={out.header.stamp.sec}.{out.header.stamp.nanosec}"
            )

            self._last_odom_time = cur_time
        except Exception as e:
            self.get_logger().warning(f'Odom integration error: {e}')


def main():
    rclpy.init()
    node = GZJointStateBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
