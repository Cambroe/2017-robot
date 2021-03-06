import math

from components import swervemodule
from robotpy_ext.common_drivers import navx

from magicbot.magic_tunable import tunable


class PositionTracker:

    fl_module = swervemodule.SwerveModule
    fr_module = swervemodule.SwerveModule
    rl_module = swervemodule.SwerveModule
    rr_module = swervemodule.SwerveModule

    x_pos = tunable(0)
    y_pos = tunable(0)

    def setup(self):
        self.enabled = False

        self._position = {
                'y': 0,
                'x': 0,
                'rcw': 0
        }

        self._zeros = {
                'front_left': 0,
                'rear_right': 0,
                'rear_left': 0,
                'front_right': 0
        }

        self.modules = {
                'front_right': self.fr_module,
                'front_left': self.fl_module,
                'rear_left': self.rl_module,
                'rear_right': self.rr_module
        }

        self.module_torque_angle = {
                'front_right': (math.pi / 4),
                'front_left': -(math.pi / 4),
                'rear_left': (math.pi / 4),
                'rear_right': -(math.pi / 4)
        }

        self.width = (22/12)/2
        self.length = (18.5/12)/2

    def get_diff(self, value, old_zero):
        diff = value - old_zero
        new_zero = value

        return diff, new_zero

    def separate_y(self, dist, theta):
        """
        This function separates the movment in the y direction with wheels that 0 deg is forward.
        """

        return math.cos(theta) * dist

    def separate_x(self, dist, theta):
        """
        This function separates the movment in the x direction with wheels that 0 deg is forward.
        """

        return math.sin(theta) * dist

    def enable(self, zero_position = True):
        if not self.fl_module.has_drive_encoder or not self.rr_module.has_drive_encoder:
            if not self.rl_module.has_drive_encoder or not self.fr_module.has_drive_encoder:
                raise 'Not enough drive encoders to predict position'

        self.enabled = True

        if zero_position:
            self.reset()

    def disable(self, zero_position=False):
        self.enabled = False

        if zero_position:
            self._position['y'] = 0.0
            self._position['x'] = 0.0
            self._position['rcw'] = 0.0

    def reset(self):
        self._position['y'] = 0.0
        self._position['x'] = 0.0
        self._position['rcw'] = 0.0

        self._zeros['front_left'] = self.fl_module.get_drive_encoder_distance()
        self._zeros['rear_right'] = self.rr_module.get_drive_encoder_distance()
        self._zeros['rear_left'] = self.rl_module.get_drive_encoder_distance()
        self._zeros['front_right'] = self.fr_module.get_drive_encoder_distance()

    def get_x(self):
        return self._position['x']

    def get_y(self):
        return self._position['y']

    def _calculate(self):
        encoders = 0

        radius = math.hypot(self.length, self.width)

        x = 0
        y = 0
        rcw = 0

        for key in self.modules:
            if self.modules[key].has_drive_encoder:
                dist = self.modules[key].get_drive_encoder_distance()
                theta = swervemodule.SwerveModule.voltage_to_rad(self.modules[key].get_voltage())

                dist, self._zeros[key] = self.get_diff(dist, self._zeros[key])

                x += -self.separate_x(dist, theta)
                y += self.separate_y(dist, theta)

                # Rotation calculations
                theta += self.module_torque_angle[key]

                if key == 'rear_right' or key == 'front_right':
                    dist *= -1

                rcw += radius * (math.cos(theta) * dist)

                encoders += 1

        self._position['x'] += x * (1/encoders)
        self._position['y'] += y * (1/encoders)
        self._position['rcw'] += rcw * (1/encoders)

    def execute(self):
        if self.enabled:
            self._calculate()

        self.x_pos = self._position['x']
        self.y_pos = self._position['y']


class FCPositionTracker(PositionTracker):
    navx = navx.AHRS

    def separate_y(self, dist, theta):
        """
        Separate the movement in the y direction with wheels for which 0 deg is forward.
        """
        theta = (theta - math.radians(self.navx.yaw)) % (2 * math.pi)
        return super().separate_y(dist, theta)

    def separate_x(self, dist, theta):
        """
        Separate the movment in the x direction with wheels for which 0 deg is forward.
        """
        theta = (theta - math.radians(self.navx.yaw)) % (2 * math.pi)

        return super().separate_x(dist, theta)
