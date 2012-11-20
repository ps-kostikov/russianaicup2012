import math
import time
import sys

from model.FireType import FireType
from model.TankType import TankType
from model.ShellType import ShellType
from model.BonusType import BonusType
from model.Unit import Unit

from geometry import *
import geometry
from utils import *
import utils
from constants import *
import constants
from assessments import *
import assessments
import prediction


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def within(self, world):
        return 0 <= self.x < world.width and 0 <= self.y < world.height


def within_world(x, y, world):
    return Point(x, y).within(world)


def within_unit(x, y, unit):
    # FIXME use unit angle
    return unit.x - unit.width / 2. <= x <= unit.x + unit.width / 2. and \
            unit.y - unit.height / 2. <= y <= unit.y + unit.height / 2.


class Zone:
    def __init__(self, x, y, r=constants.ZONE_RADIUS):
        self.x = x
        self.y = y
        self.r = r

    def get_point_to_move(self, tank):
        # FIXME
        return Point(self.x, self.y)

        if math.hypot(tank.x - self.x, tank.y - self.y) <= self.r:
            return Point(tank.x, tank.y)

        tvx = math.cos(tank.angle)
        tvy = math.sin(tank.angle)
        npx, npy = geometry.get_nearest_point(tank.x, tank.y, tank.x + tvx, tank.y + tvy,
                self.x, self.y)

        vx = npx - self.x
        vy = npy - self.y
        ll = math.hypot(vx, vy)
        vx /= ll
        vy /= ll

        # FIXME rather rude but can be usefull
        return Point(self.x + vx * self.r, self.y + vy * self.r)


def make_zone(bonus, tank):
    # r = min(bonus.width / 2., bonus.height / 2.) + min(tank.width / 2., tank.height / 2.)
    r = min(bonus.width / 2., bonus.height / 2.)
    return Zone(bonus.x, bonus.y, r)



def get_zones(world):
    delta = 80.
    min_x, min_y = delta, delta
    max_x, max_y = 1280 - delta, 800 - delta

    w_parts_number = int((max_x - min_x) / (2. * constants.ZONE_RADIUS))
    w_step = (max_x - min_x) / w_parts_number

    h_parts_number = int((max_y - min_y) / (2. * constants.ZONE_RADIUS))
    h_step = (max_y - min_y) / h_parts_number

    base = delta
    x = y = base
    res = []
    while x <= max_x + 1.:
        while y <= max_y + 1.:
            append = True
            for obstacle in world.obstacles:
                rad = math.hypot(obstacle.width / 2., obstacle.height / 2.) + 30.
                if math.hypot(x - obstacle.x, y - obstacle.y) < rad:
                    append = False
                    break
            if append:
                res.append(Zone(x, y))
            y += h_step
        y = base
        x += w_step

    return res


def get_enemy(me, world):
    enemies = all_enemies(world)
    # teammates = all_teammates(world)
    def efficiency(enemy):
        return possible_score(me, enemy, world) / time_before_hit(tank=me, target=enemy)
    return max(enemies, key=lambda e: efficiency(e))


def should_give_way(me, world):
    if world.tick > 30:
        return False
    team = all_teammates(world)
    max_id = max([t.id for t in team])
    return me.id < max_id


def fire_to(goal, me, world, move):
    # max_premium_distance = math.hypot(world.width, world.height) / 2
    max_premium_distance = 600

    distance = me.get_distance_to_unit(goal)
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

    possible_shell = utils.make_possible_shell(me)

    if abs(turret_angle) > max_fire_angle:
        move.fire_type = FireType.NONE
    elif is_goal_blocked(possible_shell, goal, world):
        move.fire_type = FireType.NONE
    elif should_give_way(me, world):
        move.fire_type = FireType.NONE
    else:
        if distance > max_premium_distance:
            move.fire_type = FireType.REGULAR
        else:
            move.fire_type = FireType.PREMIUM_PREFERRED

    # move.fire_type = FireType.NONE


def move_to_unit(goal, me, world, move):
    min_dist = 20
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
    angle_for_simple = math.pi / 4
    vsx = shell.speedX
    vsy = shell.speedY

    vmx = math.cos(me.angle)
    vmy = math.sin(me.angle)

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
            power = -power

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

        # if 1, 1 then move front using left track
        def make_move(direction, side):
            if side > 0:
                move.left_track_power = direction
                move.right_track_power = direction * angle_share
            else:
                move.right_track_power = direction
                move.left_track_power = direction * angle_share

        # can rotate, direction > 1 if forward, side > 1 if use side track
        def can_rotate(direction, side):
            res = has_place(fake_me, world, direction, -side)
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


def new_best_avoid_shells(shells, me, world, move):
    strategies = [
            (1., 1.),
            (-1., -1.),
            (1., 0.5),
            (0.5, 1),
            (-1., -0.5),
            (-0.5, -1.),
            (0.75, -1.),
            (-1., 0.75),
            ]

    def damage(s):
        res = 0.
        for shell in shells:
            res += prediction.damage(me, shell, world, s[0], s[1])
        return res

    stategy = min(strategies, key=lambda s: damage(s))
    move.left_track_power = stategy[0]
    move.right_track_power = stategy[1]
    # print world.tick, ":", stategy[0], stategy[1], \
    #         prediction.damage(me, shell, world, stategy[0], stategy[1])
    return True


def avoid_shells(me, world, move):

    dangerous_shells = filter(lambda s: is_shell_dangerous(me, s, world), world.shells)

    shells_to_avoid = filter(lambda s: not is_shell_unavoidable(me, s), dangerous_shells)

    if len(shells_to_avoid) == 0:
        return False

    # premium_shells_to_avoid = filter(lambda s: s.type == ShellType.PREMIUM, shells_to_avoid)
    # if len(premium_shells_to_avoid) > 0:
    #     shell_to_avoid = min(premium_shells_to_avoid, key=lambda s: time_to_shell_hit(me, s))
    # else:
    #     shell_to_avoid = min(shells_to_avoid, key=lambda s: time_to_shell_hit(me, s))

    # return avoid_shell(shell_to_avoid, me, world, move)
    return new_best_avoid_shells(shells_to_avoid, me, world, move)


def get_bonus_rating(me, bonus):
    time = assessments.time_to_get(me, bonus)
    if time < 0.01:
        time = 0.01
    return get_bonus_factor(me, bonus) / time


def get_best_zone(me, world):
    zones = get_zones(world)
    neighbour_zones = filter(lambda z: me.get_distance_to(z.x, z.y) < constants.ZONE_RADIUS * 2 * 1.6,
            zones)
    enemies = all_enemies(world)
    team_power = get_team_power(world)
    team = all_teammates_without_me(world, me)

    def team_addition_value(distance):
        # 0 -> -2.
        # norm -> 0.
        # max -> -1.
        min_norm_dist = 120
        max_norm_dist = 400
        max_dist = 1000
        if distance < min_norm_dist:
            return (2. * distance) / float(min_norm_dist) - 2.
        elif min_norm_dist <= distance <= max_norm_dist:
            return 0.
        else:
            return (max_norm_dist - distance) / (max_dist - max_norm_dist)

    def team_addition(zone):
        res = 0
        for t in team:
            res += team_addition_value(math.hypot(zone.x - t.x, zone.y - t.y))
        return res

    def angle_to_coeff(angle):
        limit = math.pi / 2.
        if angle > limit:
            return 2.
        if angle < 0:
            return 1.
        return 1. + angle / limit

    def enemy_addition_value(distance):
        min_dist = 90.
        if distance > min_dist:
            return 0.
        return -2. + (2. * distance) / min_dist

    def enemy_addition(zone):
        res = 0
        for e in enemies:
            res += enemy_addition_value(math.hypot(zone.x - e.x, zone.y - e.y))
        coef = angle_to_coeff(utils.angle_fork(zone, enemies))
        return res * coef

    def damage(zone):
        # res = 0
        # for e in enemies:
        #     res += get_power(e) * damage_probability(e.x, e.y, zone.x, zone.y)
        # return res

        res = 0
        for e in enemies:
            my_damage_prob = damage_probability(e.x, e.y, zone.x, zone.y)
            if len(team) > 0:
                best_team_target = max(team, key=lambda t: damage_probability(e.x, e.y, t.x, t.y))
                if damage_probability(e.x, e.y, best_team_target.x, best_team_target.y) > my_damage_prob:
                    continue

            res += get_power(e) * my_damage_prob
        return res

    def my_damage(zone):
        # res = 0
        # power = get_power(me)
        # for e in enemies:
        #     res += power * damage_probability(zone.x, zone.y, e.x, e.y)

        # angle_fork_sum = 0.
        # for e in enemies:
        #     angle_fork_sum += utils.angle_fork(e, [zone] + team)
        # average_angle_fork = angle_fork_sum / len(enemies)
        # coef = angle_to_coeff(average_angle_fork)
        # return res * coef

        target = max(enemies, key=lambda e: damage_probability(zone.x, zone.y, e.x, e.y))
        res = get_power(me) * damage_probability(zone.x, zone.y, target.x, target.y)
        angle_fork = utils.angle_fork(target, [zone] + team)
        coef = angle_to_coeff(angle_fork)
        return res * coef


    def value(zone):
        enemy_power = 1 - team_power
        return enemy_addition(zone) + \
                0.3 * team_addition(zone) + \
                team_power * my_damage(zone) - \
                enemy_power * damage(zone)


    res = max(neighbour_zones, key=lambda z: value(z))
    # if world.tick == 1:
    #     if len(team) == 0 or me.id < min(team, key=lambda t: t.id).id:
    #         print_zones(world, value)
    return res


def get_strategic_goal(me, world):
    # enemies = all_enemies(world)

    team = all_teammates_without_me(world, me)
    usefull_bonuses = filter(lambda b: assessments.is_bonus_usefull(me, b, world), world.bonuses)
    for teammate in team:
        usefull_bonuses = filter(
                lambda b: get_bonus_rating(me, b) > get_bonus_rating(teammate, b), usefull_bonuses)

    if len(usefull_bonuses) > 0:
        bonus = max(usefull_bonuses, key=lambda b: get_bonus_rating(me, b))
        return make_zone(bonus, me)

    return get_best_zone(me, world)


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

    bother_time = 40
    dangerous_enemies = filter(lambda e: enemy_is_going_hit_only_me(me, e, enemies), enemies)
    very_dangerous_enemies = filter(
            lambda e: time_before_hit(tank=e, target=me) <= bother_time, dangerous_enemies)
    if len(very_dangerous_enemies) != 1:
        return False

    enemy = very_dangerous_enemies[0]

    absolute_angle_to_me = math.atan2(me.y - enemy.y, me.x - enemy.x)

    turret_angle_to_me = enemy.get_turret_angle_to_unit(me)
    if rad_to_degree(turret_angle_to_me) > 10:
        turret_angle_to_me = degree_to_rad(10)
    if rad_to_degree(turret_angle_to_me) < -10:
        turret_angle_to_me = degree_to_rad(-10)

    possible_shell_angle = absolute_angle_to_me - turret_angle_to_me

    spx = math.cos(possible_shell_angle)
    spy = math.sin(possible_shell_angle)
    spx = spx * SHELL_AVERAGE_SPEED
    spy = spy * SHELL_AVERAGE_SPEED

    possible_shell = Unit(0, width=10, height=10, x=enemy.x, y=enemy.y,
            speed_x=spx, speed_y=spy, angle=0, angular_speed=0)

    if is_goal_blocked(possible_shell, me, world):
        return False

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


def print_zones(world, func):
    delta = 80.
    min_x, min_y = delta, delta
    max_x, max_y = 1280 - delta, 800 - delta

    w_parts_number = int((max_x - min_x) / (2. * constants.ZONE_RADIUS))
    w_step = (max_x - min_x) / w_parts_number

    h_parts_number = int((max_y - min_y) / (2. * constants.ZONE_RADIUS))
    h_step = (max_y - min_y) / h_parts_number

    def marker(x, y):
        for tank in world.tanks:
            if tank.get_distance_to(x, y) < constants.ZONE_RADIUS:
                return 'M' if tank.teammate else 'E'
        return ''

    base = delta
    x = y = base
    with open('{0}.txt'.format(world.tick), 'w') as out:
        while y <= max_y + 1.:
            while x <= max_x + 1.:
                append = True
                for obstacle in world.obstacles:
                    rad = math.hypot(obstacle.width / 2., obstacle.height / 2.) + 30.
                    if math.hypot(x - obstacle.x, y - obstacle.y) < rad:
                        append = False
                        break
                if append:
                    out.write('{0:.2f}{1}\t'.format(func(Zone(x, y)), marker(x, y)))
                else:
                    out.write('----\t')
                x += w_step
            out.write('\n')
            x = base
            y += h_step


class MyStrategy:
    def __init__(self):
        self.health = 100.
        self.predicted_damage = 0.

    def move(self, me, world, move):
        begin = time.time()

        enemy = get_enemy(me, world)

        fire_to(enemy, me, world, move)

        if not avoid_shells(me, world, move):
            if not avoid_possible_shells(me, world, move):
                zone = get_strategic_goal(me, world)
                point = zone.get_point_to_move(me)
                if not move_to_unit(point, me, world, move):
                    help_turret(me, move)

        # print world.tick, ";", time.time() - begin

    def select_tank(self, tank_index, team_size):
        return TankType.MEDIUM