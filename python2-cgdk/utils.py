'''
Precise functions without any heuristics
'''

from geometry import *
from constants import *


def get_borders(unit):
    vx = math.cos(unit.angle)
    vy = math.sin(unit.angle)
    nvx = vy
    nvy = -vx

    # l - left, f = front, r - right, b - back
    lf_x = unit.x + (unit.width * vx + unit.height * nvx) / 2.
    lf_y = unit.y + (unit.width * vy + unit.height * nvy) / 2.

    rf_x = unit.x + (unit.width * vx - unit.height * nvx) / 2.
    rf_y = unit.y + (unit.width * vy - unit.height * nvy) / 2.

    lb_x = unit.x + (-unit.width * vx + unit.height * nvx) / 2.
    lb_y = unit.y + (-unit.width * vy + unit.height * nvy) / 2.

    rb_x = unit.x + (-unit.width * vx - unit.height * nvx) / 2.
    rb_y = unit.y + (-unit.width * vy - unit.height * nvy) / 2.

    res = []
    res.append((lf_x, lf_y, rf_x, rf_y))
    res.append((rf_x, rf_y, rb_x, rb_y))
    res.append((rb_x, rb_y, lb_x, lb_y))
    res.append((lb_x, lb_y, lf_x, lf_y))
    return res


def alive(tank):
    return tank.crew_health > 0 and tank.hull_durability > 0


def all_enemies(world):
    '''alive tanks not in my team'''
    return filter(lambda t: alive(t) and not t.teammate, world.tanks)


def all_teammates(world):
    '''alive tanks in my team'''
    return filter(lambda t: alive(t) and t.teammate, world.tanks)


def get_turret_speed(tank):
    '''return turret speed in rad/tick'''
    live_percentage = float(tank.crew_health) / float(tank.crew_max_health)
    return degree_to_rad(0.5 * (1 + live_percentage))


def time_before_hit(tank, target):
    angle_to_target = tank.get_turret_angle_to_unit(target)
    distance_to_target = tank.get_distance_to_unit(target)

    base_turret_speed = get_turret_speed(tank)
    if angle_to_target * tank.angular_speed > 0:
        total_angle_speed = base_turret_speed + abs(tank.angular_speed)
    else:
        total_angle_speed = base_turret_speed - abs(tank.angular_speed)
    eps = 1.e-4
    if abs(total_angle_speed) < eps:
        total_angle_speed = eps

    time_before_shot = max(tank.remaining_reloading_time, abs(angle_to_target) / total_angle_speed)
    flight_time = distance_to_target / SHELL_AVERAGE_SPEED
    return flight_time + time_before_shot + 1


def is_goal_blocked_by(shell, goal, blocker):
    borders = get_borders(blocker)

    gx, gy = get_nearest_point(shell.x, shell.y,
            shell.x + shell.speedX, shell.y + shell.speedY,
            goal.x, goal.y)

    vx = gx - shell.x
    vy = gy - shell.y
    vlen = math.hypot(vx, vy)
    if vlen < 0.0001:
        vlen = 0.0001
    vx /= vlen
    vy /= vlen

    nvx = vy
    nvy = -vx

    pessimistic_coeff = 1.5
    dx = pessimistic_coeff * (nvx * SHELL_HEIGHT / 2.)
    dy = pessimistic_coeff * (nvy * SHELL_HEIGHT / 2.)
    main_line = (goal.x, goal.y, shell.x, shell.y)
    # print main_line
    border_line1 = (goal.x + dx, goal.y + dy, shell.x + dx, shell.y + dy)
    border_line2 = (goal.x - dx, goal.y - dy, shell.x - dx, shell.y - dy)

    for border in borders:
        x1, y1, x2, y2 = border
        if are_intervals_intersect(x1, y1, x2, y2, *main_line):
            return True
        if are_intervals_intersect(x1, y1, x2, y2, *border_line1):
            return True
        if are_intervals_intersect(x1, y1, x2, y2, *border_line2):
            return True

    return False


def is_goal_blocked(shell, goal, world):
    blockers = world.bonuses + filter(lambda t: not alive(t), world.tanks) + filter(lambda t: t.teammate, world.tanks)
    blockers = filter(lambda o: o.get_distance_to_unit(shell) > 0.01 and
            o.get_distance_to_unit(goal) > 0.01, blockers)

    for blocker in blockers:
        if is_goal_blocked_by(shell, goal, blocker):
            return True
    return False


