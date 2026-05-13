import os
from glob import glob
from setuptools import setup, find_packages

package_name = 'rover_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='busragizemyilmaz',
    maintainer_email='busragizemyilmaz.dev@gmail.com',
    description='Rover teleop control package',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
	    'console_scripts': [
		'mod1 = rover_control.rover_teleop_mod1:main',
		'mod2 = rover_control.rover_teleop_mod2:main',
	    ],
	},
)
