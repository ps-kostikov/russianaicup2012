'''
Precise functions without any heuristics
'''

from model.Unit import Unit

from geometry import *
import geometry
from constants import *
import constants


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


def get_world_borders():
    x = constants.WORLD_WIDTH / 2.
    y = constants.WORLD_HEIGHT / 2.
    fake_world_unit = Unit(0,
            width=constants.WORLD_WIDTH,
            height=constants.WORLD_HEIGHT,
            x=x, y=y,
            speed_x=0, speed_y=0,
            angle=0, angular_speed=0)
    return get_borders(fake_world_unit)


def alive(tank):
    return tank.crew_health > 0 and tank.hull_durability > 0


def is_teammate(tank, other_tank):
    return tank.player_name == other_tank.player_name


def other_tanks(world, tank):
    return filter(lambda t: t.id != tank.id, world.tanks)


def all_enemies(world):
    '''alive tanks not in my team'''
    return filter(lambda t: alive(t) and not t.teammate, world.tanks)


def all_teammates(world):
    '''alive tanks in my team'''
    return filter(lambda t: alive(t) and t.teammate, world.tanks)


def all_teammates_without_me(world, me):
    return filter(lambda t: t.id != me.id, all_teammates(world))


def alive_team_number(world):
    alive_tanks = filter(lambda t: alive(t), world.tanks)
    player_names = set([t.player_name for t in alive_tanks])
    return len(player_names)


def life_factor(tank):
    '''return factor that reduce turret and track speeds'''
    live_percentage = float(tank.crew_health) / float(tank.crew_max_health)
    return 0.5 * (1. + live_percentage)


def get_turret_speed(tank):
    '''return turret speed in rad/tick'''
    return degree_to_rad(life_factor(tank))


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
    main_line = (gx, gy, shell.x, shell.y)
    border_line1 = (gx + dx, gy + dy, shell.x + dx, shell.y + dy)
    border_line2 = (gx - dx, gy - dy, shell.x - dx, shell.y - dy)

    for border in borders:
        x1, y1, x2, y2 = border
        if are_intervals_intersect(x1, y1, x2, y2, *main_line):
            return True
        if are_intervals_intersect(x1, y1, x2, y2, *border_line1):
            return True
        if are_intervals_intersect(x1, y1, x2, y2, *border_line2):
            return True

    return False


def get_blocker(shell, goal, world):
    blockers = world.bonuses + \
            filter(lambda t: not alive(t), world.tanks) + \
            filter(lambda t: t.teammate, world.tanks) + \
            world.obstacles
    blockers = filter(lambda o: o.get_distance_to_unit(shell) > 0.01 and
            o.get_distance_to_unit(goal) > 0.01, blockers)

    for blocker in blockers:
        if is_goal_blocked_by(shell, goal, blocker):
            return blocker
    return None


def get_static_blocker(shell, goal, world):
    blockers = filter(lambda t: not alive(t), world.tanks) + world.obstacles
    blockers = filter(lambda o: o.get_distance_to_unit(shell) > 0.01 and
            o.get_distance_to_unit(goal) > 0.01, blockers)

    for blocker in blockers:
        if is_goal_blocked_by(shell, goal, blocker):
            return blocker
    return None


def get_static_blocker_point(point, goal, world):
    shell = make_possible_shell_to_target(point, goal)
    return get_static_blocker(shell, goal, world)


def is_goal_static_blocked(shell, goal, world):
    blocker = get_static_blocker(shell, goal, world)
    return blocker is not None


def is_goal_static_blocked_point(point, goal, world):
    shell = make_possible_shell_to_target(point, goal)
    return is_goal_static_blocked(shell, goal, world)


def is_goal_blocked(shell, goal, world):
    blocker = get_blocker(shell, goal, world)
    return blocker is not None


def is_goal_blocked_point(point, goal, world):
    shell = make_possible_shell_to_target(point, goal)
    return is_goal_blocked(shell, goal, world)


def make_possible_shell_to_target(tank, target):
    shell_angle = math.atan2(target.y - tank.y, target.x - tank.x)
    tvx = math.cos(shell_angle)
    tvy = math.sin(shell_angle)

    return Unit(0, width=SHELL_WIDTH, height=SHELL_HEIGHT,
            x=tank.x,
            y=tank.y,
            speed_x=tvx * SHELL_AVERAGE_SPEED,
            speed_y=tvy * SHELL_AVERAGE_SPEED,
            angle=shell_angle, angular_speed=0)


def make_possible_shell(tank):
    shell_angle = tank.angle + tank.turret_relative_angle
    tvx = math.cos(shell_angle)
    tvy = math.sin(shell_angle)

    return Unit(0, width=SHELL_WIDTH, height=SHELL_HEIGHT,
            x=tank.x,
            y=tank.y,
            speed_x=tvx * SHELL_AVERAGE_SPEED,
            speed_y=tvy * SHELL_AVERAGE_SPEED,
            angle=shell_angle, angular_speed=0)


def angle_fork_between_two(goal, tank1, tank2):
    angle1 = math.atan2(goal.y - tank1.y, goal.x - tank1.x)
    angle2 = math.atan2(goal.y - tank2.y, goal.x - tank2.x)

    res = max(angle1, angle2) - min(angle1, angle2)
    while res > math.pi:
        res -= math.pi
    return res


def angle_fork(goal, tanks):
    '''return max angle in rads'''
    res = 0.
    for i in range(len(tanks)):
        for j in range(len(tanks)):
            if i <= j:
                continue
            res = max(res, angle_fork_between_two(goal, tanks[i], tanks[j]))
    return res
