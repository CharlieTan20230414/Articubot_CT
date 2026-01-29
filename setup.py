from setuptools import setup

package_name = 'Articubot_CT'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/rsp.launch.py', 'launch/spawn_Articubot_CT.launch.py']),
        ('share/' + package_name + '/config', ['config/empty.yaml']),
        ('share/' + package_name + '/description', ['description/robot.urdf.xacro', 'description/robot_core.xacro', 'description/gazebo_control.xacro', 'description/inertial_macros.xacro']),
        ('share/' + package_name + '/worlds', ['worlds/empty.world']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='CharlieTan20230414',
    maintainer_email='jianan_tan20210829@126.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'odom_to_tf = Articubot_CT.odom_to_tf:main',
            'check_tf = Articubot_CT.check_tf:main',
        ],
    },
)
