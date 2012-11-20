import math

from model.ShellType import ShellType
from model.Unit import Unit
from model.Tank import Tank
from model.Shell import Shell

import geometry
import utils
import assessments
import constants

REGULAR_COEFF = 0.995
PREMIUM_COEFF = 0.99


def next_shell(shell, world, tick=1):
    new_x = shell.x
    new_y = shell.y
    new_speed_x = shell.speedX
    new_speed_y = shell.speedY

    for i in range(tick):
        new_x = new_x + new_speed_x
        new_y = new_y + new_speed_y
        if shell.type == ShellType.REGULAR:
            new_speed_x = new_speed_x * REGULAR_COEFF
            new_speed_y = new_speed_y * REGULAR_COEFF
        else:
            new_speed_x = new_speed_x * PREMIUM_COEFF
            new_speed_y = new_speed_y * PREMIUM_COEFF

    new_shell = Shell(id=shell.id, player_name=shell.player_name, width=shell.width, height=shell.height,
            x=new_x,
            y=new_y,
            speed_x=new_speed_x,
            speed_y=new_speed_y,
            angle=shell.angle, angular_speed=shell.angular_speed, type=shell.type)
    return new_shell


def cross_boundaries(tank, world):
    tank_borders = utils.get_borders(tank)

    for world_border in utils.get_world_borders():
        for tank_border in tank_borders:
            x1, y1, x2, y2 = tank_border
            if geometry.are_intervals_intersect(x1, y1, x2, y2, *world_border):
                return True

    def can_cross(unit):
        unit_size = math.hypot(unit.width / 2., unit.height / 2.)
        tank_size = math.hypot(tank.width / 2., tank.height / 2.)
        return unit_size + tank_size > math.hypot(unit.x - tank.x, unit.y - tank.y)

    # for unit in world.obstacles:
    # for unit in world.obstacles + utils.other_tanks(world, tank):
    for unit in filter(lambda u: can_cross(u), world.obstacles + utils.other_tanks(world, tank)):
        for border in utils.get_borders(unit):
            for tank_border in tank_borders:
                x1, y1, x2, y2 = tank_border
                if geometry.are_intervals_intersect(x1, y1, x2, y2, *border):
                    return True

    return False


def next_tank(tank, world, move_left, move_right, tick=1):
    if move_left < 0:
        move_left *= 0.75

    if move_right < 0:
        move_right *= 0.75

    move_left *= utils.life_factor(tank)
    move_right *= utils.life_factor(tank)

    angle_a = 0.000627876445651 / 1.5
    a = 0.1

    nsx = tank.speedX
    nsy = tank.speedY
    nx = tank.x
    ny = tank.y
    nsa = tank.angular_speed
    na = tank.angle

    for i in range(tick):
        nx = nx + nsx
        ny = ny + nsy
        nsx = nsx + a * (move_right + move_left) * math.cos(na)
        nsy = nsy + a * (move_right + move_left) * math.sin(na)
        na = na + nsa
        nsa = nsa + angle_a * (move_left - move_right)

    new = Tank(tank.id,
            x=nx, y=ny,
            speed_x=nsx, speed_y=nsy, angle=na, angular_speed=nsa,
            player_name=tank.player_name,
            teammate_index=tank.teammate_index,
            turret_relative_angle=tank.turret_relative_angle,
            crew_health=tank.crew_health,
            hull_durability=tank.hull_durability,
            reloading_time=tank.reloading_time,
            remaining_reloading_time=tank.remaining_reloading_time,
            premium_shell_count=tank.premium_shell_count,
            teammate=tank.teammate,
            type=tank.type
            )

    if cross_boundaries(new, world):
        new.x = tank.x
        new.y = tank.y
    return new


def touch_next_tick(shell, next_shell, tank):
    return utils.is_goal_blocked_by(shell, next_shell, tank)


def damage(tank, shell, world, move_left, move_right):
    '''return damage if tank will use move_left/move_right move strategy'''
    if math.hypot(shell.speedX, shell.speedY) < 1.:
        return 0.

    tank_prev = tank
    shell_prev = shell
    dist_prev = tank_prev.get_distance_to_unit(shell_prev)

    tank_next = next_tank(tank_prev, world, move_left, move_right)
    shell_next = next_shell(shell_prev, world)
    dist_next = tank_next.get_distance_to_unit(shell_next)

    if touch_next_tick(shell, shell_next, tank_next):
        return assessments.shell_damage(shell, tank_next)

    while (dist_next < dist_prev):
        if dist_next / constants.SHELL_AVERAGE_SPEED > 10:
            tick_count = 5
        else:
            tick_count = 1

        shell_prev = shell_next
        tank_prev = tank_next
        dist_prev = dist_next

        tank_next = next_tank(tank_prev, world, move_left, move_right, tick_count)
        shell_next = next_shell(shell_prev, world, tick_count)
        dist_next = tank_next.get_distance_to_unit(shell_next)

        if touch_next_tick(shell, shell_next, tank_next):
            return assessments.shell_damage(shell, tank_next)

        if assessments.shell_damage(shell, tank_next) < 0.0001:
            return 0.

    return 0.
