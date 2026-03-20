from setuptools import find_packages, setup

package_name = 'rover_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='taha',
    maintainer_email='muhibtahaboy42@gmail.com',
    description='Rover kol teleop ve kontrol paketi',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'mod1 = rover_control.rover_teleop_mod1:main',
            'mod2 = rover_control.rover_teleop_mod2:main',
        ],
    },
)
