import math
from model.FireType import FireType
from model.TankType import TankType
from model.ShellType import ShellType
from model.BonusType import BonusType
from model.Unit import Unit

from geometry import *
from utils import *
from constants import *
import constants
from assessments import *

index = 0


def log_print(s):
    global index
    index += 1
    print s, index


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def within(self, world):
        return 0 <= self.x < world.width and 0 <= self.y < world.height


def within_world(x, y, world):
    return Point(x, y).within(world)


class Zone:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.r = constants.ZONE_RADIUS

    def get_point_to_move(self, tank):
        #FIX ME add some usefull here
        return self.x, self.y

def get_zones():
    x, y = 0., 0.
    res = []
    while x <= constants.WORLD_WIDTH:
        while y <= constants.WORLD_HEIGHT:
            res.append(Zone(x, y))
            y += constants.ZONE_RADIUS
        y = 0.
        x += constants.ZONE_RADIUS
    return res


def get_enemy(me, world):
    enemies = all_enemies(world)
    # teammates = all_teammates(world)
    def efficiency(enemy):
        return possible_score(me, enemy, world) / time_before_hit(tank=me, target=enemy)
    return max(enemies, key=lambda e: efficiency(e))


def fire_to(goal, me, world, move):
    max_premium_distance = math.hypot(world.width, world.height) / 2

    distance = me.get_distance_to_unit(goal)
    # goal_size = min(goal.width, goal.height)
    goal_size = 15
    max_fire_angle = math.atan2(goal_size, distance)

    time_to_reach = distance / SHELL_AVERAGE_SPEED

    predicted_x = goal.x + (time_to_reach * goal.speedX) / 2.
    predicted_y = goal.y + (time_to_reach * goal.speedY) / 2.

    turret_angle = me.get_turret_angle_to(predicted_x, predicted_y)

    eps = degree_to_rad(1)
    if abs(turret_angle) < eps:
        move.turret_turn = 0
    else:
        move.turret_turn = 1. if turret_angle > 0 else -1.

    shell_angle = me.angle + me.turret_relative_angle
    tvx = math.cos(shell_angle)
    tvy = math.sin(shell_angle)

    possible_shell = Unit(0, width=SHELL_WIDTH, height=SHELL_HEIGHT,
            x=me.x,
            y=me.y,
            speed_x=tvx * SHELL_AVERAGE_SPEED,
            speed_y=tvy * SHELL_AVERAGE_SPEED,
            angle=shell_angle, angular_speed=0)

    if abs(turret_angle) > max_fire_angle:
        move.fire_type = FireType.NONE
    elif is_goal_blocked(possible_shell, goal, world):
        move.fire_type = FireType.NONE
    else:
        if distance > max_premium_distance:
            move.fire_type = FireType.REGULAR
        else:
            move.fire_type = FireType.PREMIUM_PREFERRED


def move_to_unit(goal, me, world, move):
    min_dist = 5
    if math.hypot(goal.x - me.x, goal.y - me.y) < min_dist:
        return False

    x, y = goal.x, goal.y
    min_angle = math.pi / 6

    angle = me.get_angle_to(x, y)

    if -min_angle < angle < min_angle:
        move.left_track_power = 1.
        move.right_track_power = 1.
    elif angle > math.pi - min_angle or angle < -math.pi + min_angle:
        move.left_track_power = -1.
        move.right_track_power = -1.
    elif min_angle < angle < math.pi / 2:
        move.left_track_power = 1.
        move.right_track_power = -1.0
    elif -math.pi / 2 < angle < -min_angle:
        move.left_track_power = -1.0
        move.right_track_power = 1.
    elif angle > math.pi / 2:
        move.left_track_power = -1.
        move.right_track_power = 1.
    else:
        move.left_track_power = 1.
        move.right_track_power = -1.

    return True


# return True if shell path crossed me
def is_shell_dangerous(me, shell, world):
    vs_x = shell.speedX
    vs_y = shell.speedY
    speed_mod = math.hypot(shell.speedX, shell.speedY)
    if speed_mod < 0.001:
        return False

    dist_x = shell.x + vs_x * 1000
    dist_y = shell.y + vs_y * 1000

    next_shell = Unit(shell.id, width=shell.width, height=shell.height,
            x=dist_x, y=dist_y,
            speed_x=shell.speedX, speed_y=shell.speedY,
            angle=shell.angle, angular_speed=shell.angular_speed)

    time_to_touch = me.get_distance_to_unit(shell) / speed_mod
    next_me_x = me.x + time_to_touch * me.speedX
    next_me_y = me.y + time_to_touch * me.speedY
    next_me = Unit(me.id, width=me.width, height=me.height,
            x=next_me_x, y=next_me_y,
            speed_x=me.speedX, speed_y=me.speedY,
            angle=me.angle, angular_speed=me.angular_speed)

    if not is_goal_blocked_by(shell, next_shell, next_me):
        return False

    if is_goal_blocked(shell, me, world):
        return False
    return True


def time_to_shell_hit(me, shell):
    distance = me.get_distance_to_unit(shell)
    speed_mod = math.hypot(shell.speedX, shell.speedY)
    if speed_mod < 0.001:
        return False
    return distance / speed_mod


def is_shell_unavoidable(me, shell):
    return False
    # return time_to_shell_hit(me, shell) < 10


def has_place(me, world, front, left):
    mvx = math.cos(me.angle)
    mvy = math.sin(me.angle)

    left_mvx = mvy
    left_mvy = -mvx

    m_size = math.hypot(me.width, me.height)

    l_coef = 1. if left > 0 else -1.
    f_coef = 1. if front > 0 else -1.
    l_coef *= 1.
    f_coef *= 1

    px = me.x + f_coef * mvx * m_size + l_coef * left_mvx * m_size
    py = me.y + f_coef * mvy * m_size + l_coef * left_mvy * m_size

    return within_world(px, py, world)


def avoid_shell(shell, me, world, move):
    # print "shell = ", shell.x, shell.y
    angle_for_simple = math.pi / 4
    vsx = shell.speedX
    vsy = shell.speedY

    vmx = math.cos(me.angle)
    vmy = math.sin(me.angle)

    # print "VS = ", vsx, vsy
    # print "VM = ", vmx, vmy

    m_size = math.hypot(me.width, me.height)

    nx, ny = get_nearest_point(shell.x, shell.y, shell.x + vsx, shell.y + vsy, me.x, me.y)
    vnx = nx - me.x
    vny = ny - me.y
    if math.hypot(vnx, vny) < 0.000001:
        prefered_power = 1.
    else:
        norm_angle = get_angle(vmx, vmy, vnx, vny)
        prefered_power = 1. if norm_angle > math.pi / 2 else -1.

    angle = get_angle(vsx, vsy, vmx, vmy)
    if angle_for_simple < angle < math.pi - angle_for_simple:
        # simple move

        power = prefered_power
        est_x = nx + 1.5 * vmx * m_size * power
        est_y = ny + 1.5 * vmy * m_size * power

        if not within_world(est_x, est_y, world):
            # print 'avoid borderrrrr'
            power = -power

        # print power
        move.right_track_power = power
        move.left_track_power = power
        return True
    else:
        if angle <= angle_for_simple:
            angle_share = angle / angle_for_simple
        if angle >= math.pi - angle_for_simple:
            angle_share = (math.pi - angle) / angle_for_simple

        front_angle = get_angle(vmx, vmy, vsx, vsy)
        # if shell goes to front
        front = 1. if front_angle > math.pi / 2 else -1.

        # if shell goes to left board
        left = 1. if me.get_angle_to_unit(shell) < 0 else -1.

        fake_me = Unit(me.id, width=me.width, height=me.height, x=nx, y=ny,
                speed_x=me.speedX, speed_y=me.speedY, angle=me.angle, angular_speed=me.angular_speed)

        # sign of angle
        preffered_rotation = left * front
        # log_print('dir rot {0} {1} ====='.format(prefered_power, preffered_rotation))

        # if 1, 1 then move front using left track
        def make_move(direction, side):
            # log_print('front side {0} {1} ====='.format(direction, side))
            if side > 0:
                move.left_track_power = direction
                move.right_track_power = direction * angle_share
            else:
                move.right_track_power = direction
                move.left_track_power = direction * angle_share

        # can rotate, direction > 1 if forward, side > 1 if use side track
        def can_rotate(direction, side):
            res = has_place(fake_me, world, direction, -side)
            # print "can rotate ", direction, side, res
            return res

        for direction, side in [
                (prefered_power, prefered_power * preffered_rotation),
                (-prefered_power, prefered_power * preffered_rotation),
                (prefered_power, prefered_power * preffered_rotation),
                (-prefered_power, prefered_power * preffered_rotation)]:
            if can_rotate(direction, side):
                make_move(direction, side)
                return True

        return True


def avoid_shells(me, world, move):

    dangerous_shells = filter(lambda s: is_shell_dangerous(me, s, world), world.shells)

    shells_to_avoid = filter(lambda s: not is_shell_unavoidable(me, s), dangerous_shells)

    if len(shells_to_avoid) == 0:
        return False

    premium_shells_to_avoid = filter(lambda s: s.type == ShellType.PREMIUM, shells_to_avoid)
    if len(premium_shells_to_avoid) > 0:
        shell_to_avoid = min(premium_shells_to_avoid, key=lambda s: time_to_shell_hit(me, s))
    else:
        shell_to_avoid = min(shells_to_avoid, key=lambda s: time_to_shell_hit(me, s))

    return avoid_shell(shell_to_avoid, me, world, move)


def is_bonus_usefull(me, bonus):
    if bonus.type == BonusType.AMMO_CRATE:
        return True

    live_percentage = float(me.crew_health) / float(me.crew_max_health)
    hull_percentage = float(me.hull_durability) / float(me.hull_max_durability)

    if bonus.type == BonusType.MEDIKIT and live_percentage + 0.4 < hull_percentage:
        return False

    if bonus.type == BonusType.REPAIR_KIT and hull_percentage + 0.4 < live_percentage:
        return False

    return True


def get_bonus_value(me, bonus):
    '''between 1 and 10'''

    if bonus.type == BonusType.AMMO_CRATE:
        return max(1, 9 - me.premium_shell_count)

    live_percentage = float(me.crew_health) / float(me.crew_max_health)
    hull_percentage = float(me.hull_durability) / float(me.hull_max_durability)

    if bonus.type == BonusType.MEDIKIT:
        return 10 * (1 - live_percentage) + 2

    if bonus.type == BonusType.AMMO_CRATE:
        return 10 * (1 - hull_percentage) + 1
    return 1


def get_time_to_bonus(me, bonus):
    angle = abs(me.get_angle_to_unit(bonus))
    if angle > math.pi / 2:
        angle = math.pi - angle
    time_to_turn = angle * 1.5
    time_to_ride = me.get_distance_to_unit(bonus) / TANK_AVERAGE_SPEED
    return time_to_ride + time_to_turn


def get_bonus_rating(me, bonus):
    time = get_time_to_bonus(me, bonus)
    if time < 0.01:
        time = 0.01
    return get_bonus_value(me, bonus) / time



def get_best_zone(me, world):
    zones = get_zones()
    neighbour_zones = filter(lambda z: me.get_distance_to(z.x, z.y) < constants.ZONE_RADIUS * 1.6,
            zones)
    enemies = all_enemies(world)
    team_power = get_team_power(world)

    def damage(zone):
        res = 0
        for e in enemies:
            res += get_power(e) * damage_probability(e.x, e.y, zone.x, zone.y)
        return res

    def my_damage(zone):
        res = 0
        power = get_power(me)
        for e in enemies:
            res += power * damage_probability(zone.x, zone.y, e.x, e.y)
        return res

    def value(zone):
        enemy_power = 1 - team_power
        return team_power * my_damage(zone) - enemy_power * damage(zone)

    return max(neighbour_zones, key=lambda z: value(z))

def get_strategic_goal(me, world):
    enemies = all_enemies(world)

    if len(enemies) <= 1:
        if len(world.bonuses) > 0:
            goal = max(world.bonuses, key=lambda b: get_bonus_rating(me, b))
            return Point(goal.x, goal.y)

        # return Point(world.width / 2, world.height / 2)

    if len(world.bonuses) > 0:
        goal = max(world.bonuses, key=lambda b: get_bonus_rating(me, b))
        min_enemy_dist = min([me.get_distance_to_unit(e) for e in (enemies)])
        if me.get_distance_to_unit(goal) < min_enemy_dist:
            return Point(goal.x, goal.y)

    # delta = 60
    # corners = [
    #     Point(delta, delta),
    #     Point(world.width - delta, delta),
    #     Point(world.width - delta, world.height - delta),
    #     Point(delta, world.height - delta)
    #     ]

    # return min(corners, key=lambda c: me.get_distance_to_unit(c))

    best_zone = get_best_zone(me, world)
    return Point(best_zone.x, best_zone.y)


def enemy_is_going_hit_only_me(me, enemy, enemies):
    mine_time = time_before_hit(tank=enemy, target=me)
    for e in enemies:
        if e.id == enemy.id:
            continue

        if time_before_hit(tank=enemy, target=e) < mine_time:
            return False
    return True


def avoid_possible_shells(me, world, move):
    enemies = all_enemies(world)
    if len(enemies) == 0:
        return False

    # for e in enemies:
    #     if e.id != 5:
    #         print e.id, time_before_hit(tank=e, target=me)
    bother_time = 40
    dangerous_enemies = filter(lambda e: enemy_is_going_hit_only_me(me, e, enemies), enemies)
    very_dangerous_enemies = filter(
            lambda e: time_before_hit(tank=e, target=me) <= bother_time, dangerous_enemies)
    if len(very_dangerous_enemies) != 1:
        return False

    enemy = very_dangerous_enemies[0]
    # enemy = min(enemies, key=lambda e: time_before_enemy_hit_me(me, e))

    # time = time_before_enemy_hit_me(me, enemy)
    # if time > 100:
    #     return False

    # dist = me.get_distance_to_unit(enemy)
    absolute_angle_to_me = math.atan2(me.y - enemy.y, me.x - enemy.x)

    turret_angle_to_me = enemy.get_turret_angle_to_unit(me)
    if rad_to_degree(turret_angle_to_me) > 10:
        turret_angle_to_me = degree_to_rad(10)
    if rad_to_degree(turret_angle_to_me) < -10:
        turret_angle_to_me = degree_to_rad(-10)

    # print '= turret_angle_to_me = ', rad_to_degree(turret_angle_to_me)
    # print '= absolute_angle_to_me = ', rad_to_degree(absolute_angle_to_me)
    possible_shell_angle = absolute_angle_to_me - turret_angle_to_me

    spx = math.cos(possible_shell_angle)
    spy = math.sin(possible_shell_angle)
    spx = spx * SHELL_AVERAGE_SPEED
    spy = spy * SHELL_AVERAGE_SPEED

    possible_shell = Unit(0, width=10, height=10, x=enemy.x, y=enemy.y,
            speed_x=spx, speed_y=spy, angle=0, angular_speed=0)

    if is_goal_blocked(possible_shell, me, world):
        return False

    # log_print('avoid possible shell')
    return avoid_shell(possible_shell, me, world, move)


def help_turret(me, move):
    angle = move.turret_turn
    if abs(angle) < degree_to_rad(1):
        return False

    if angle > 0:
        move.left_track_power = 0.75
        move.right_track_power = -1.
    else:
        move.left_track_power = -1.
        move.right_track_power = 0.75
    return True


class MyStrategy:
    def __init__(self):
        pass

    def move(self, me, world, move):

        enemy = get_enemy(me, world)

        fire_to(enemy, me, world, move)

        if not avoid_shells(me, world, move):
            if not avoid_possible_shells(me, world, move):
                stratgic_goal = get_strategic_goal(me, world)
                if not move_to_unit(stratgic_goal, me, world, move):
                    help_turret(me, move)

    def select_tank(self, tank_index, team_size):
        return TankType.MEDIUM
