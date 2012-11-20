'''
Approximate functions for value assessments
'''

import math
from copy import copy

from model.Tank import Tank
from model.BonusType import BonusType
from model.ShellType import ShellType

from geometry import *
import geometry
import constants
from utils import *
import utils


def get_max_premium_distance(world):
    return math.hypot(world.width, world.height) / 2


def possible_usual_score(me, enemy, world):
    damage = 20
    will_be_killed = enemy.crew_health <= damage or enemy.hull_durability <= damage
    kill_addition = 25 if will_be_killed else 0
    max_score = min(damage, enemy.crew_health) + min(damage, enemy.hull_durability) + kill_addition
    min_score = 1

    dist = me.get_distance_to_unit(enemy)
    short_distance = get_max_premium_distance(world)
    max_distance = math.hypot(world.width, world.height)

    if dist <= short_distance:
        return max_score

    if dist >= max_score:
        return min_score

    probability = 1 - (dist - short_distance) / (max_distance - short_distance)

    return max(min_score, probability * max_score)


def possible_premium_score(me, enemy, world):
    damage = 35
    will_be_killed = enemy.crew_health <= damage or enemy.hull_durability <= damage
    kill_addition = 25 if will_be_killed else 0
    return min(damage, enemy.crew_health) + min(damage, enemy.hull_durability) + kill_addition


def possible_score(me, enemy, world):
    possible_shell = utils.make_possible_shell(me)
    blocker = get_blocker(possible_shell, enemy, world)
    if blocker is not None:
        if isinstance(blocker, Tank):
            if not utils.alive(blocker):
                return 0

    if me.get_distance_to_unit(enemy) < get_max_premium_distance(world) and \
            me.premium_shell_count > 0:
        return possible_premium_score(me, enemy, world)
    return possible_usual_score(me, enemy, world)


def get_power(tank):
    '''return relative strenth
    tank with full life and hull is considered to have power 1.
    '''
    life = float(tank.crew_health) / float(tank.crew_max_health)
    hull = float(tank.hull_durability) / float(tank.hull_max_durability)

    premium_max = 5
    premium_reserve = min(premium_max, tank.premium_shell_count)
    premium = float(premium_reserve) / float(premium_max)

    if life < hull:
        life_coef = 0.7 * life + 0.3 * hull
    else:
        life_coef = 0.3 * life + 0.7 * hull

    return life_coef * \
            0.5 * (1. + life) * \
            (1. + premium)


def get_team_power(world):
    enemies = all_enemies(world)
    teammates = all_teammates(world)

    enemy_power = sum([get_power(e) for e in enemies])
    team_power = sum([get_power(t) for t in teammates])

    return team_power / (team_power + enemy_power)


def damage_probability(tank_x, tank_y, goal_x, goal_y):
    '''1. if distance is 0
    0. if distance is height'''

    dist = math.hypot(tank_x - goal_x, tank_y - goal_y)
    short_dist = 600.
    max_dist = math.hypot(constants.WORLD_WIDTH, constants.WORLD_WIDTH)

    if dist < 0. or dist > max_dist:
        return 0.

    # min damage on short distance
    coeff = 0.8
    if dist <= short_dist:
        return 1. - (1. - coeff) * (dist / short_dist)

    return coeff * (1. - (dist - short_dist) / (max_dist - short_dist))


def get_bonus_factor(tank, bonus):
    new_tank = copy(tank)
    if bonus.type == BonusType.MEDIKIT:
        new_tank.crew_health = min(new_tank.crew_max_health, new_tank.crew_health + 35)
    elif bonus.type == BonusType.REPAIR_KIT:
        new_tank.hull_durability = min(new_tank.hull_max_durability, new_tank.hull_durability + 50)
    else:
        new_tank.premium_shell_count += 3

    # 0.1 for brave
    return get_power(new_tank) - get_power(tank) + 0.1


def time_to_get(tank, unit):
    angle = abs(tank.get_angle_to_unit(unit))
    if angle > math.pi / 2:
        angle = math.pi - angle
    time_to_turn = angle * 1.5
    time_to_ride = tank.get_distance_to_unit(unit) / TANK_AVERAGE_SPEED
    return time_to_ride + time_to_turn


def is_bonus_usefull(me, bonus, world):
    factor = get_bonus_factor(me, bonus)
    time = time_to_get(me, bonus)

    enemies = utils.all_enemies(world)
    teammates = utils.all_teammates_without_me(world, me)

    def count_damage(goal, enemy):
        if abs(geometry.get_angle(
                enemy.x - me.x, enemy.y - me.y, enemy.x - goal.x, enemy.y - goal.y)) < math.pi / 2:
            x, y = goal.x, goal.y
        else:
            # FIXME more correct here cause me and goal is not equivalent here
            x, y = geometry.get_nearest_point(me.x, me.y, goal.x, goal.y, enemy.x, enemy.y)

        goal_damage = damage_probability(enemy.x, enemy.y, x, y)
        for e in enemies + teammates:
            if utils.is_teammate(e, enemy):
                continue
            if damage_probability(enemy.x, enemy.y, e.x, e.y) > goal_damage:
                return 0.
        return goal_damage

    # brave_coeff = max(0.4, (len(enemies) - len(teammates) + 1) * 0.2)
    brave_coeff = 0.8
    damage = brave_coeff * sum([count_damage(bonus, e) for e in enemies])

    #  20. / 100. = 0.2 - damage from one full hit
    # 150. - base recharge tick time
    k = 0.2 / 150.

    return factor > k * damage * time


def coeff_by_angle(shell, angle):
    '''angle in degrees'''
    min_value, max_value = 0., 1.
    if shell.type == ShellType.REGULAR:
        ricochet_angle = 60.
        if angle > ricochet_angle:
            return 0.
        else:
            return (max_value + ((min_value - max_value) * angle) / ricochet_angle)
    else:
        return 2. * (max_value + ((min_value - max_value) * angle) / 90.)


def coeff_by_dist_factor(dist_factor):
    '''dist - from 0. to 1.'''
    return 1. - 0.2 * dist_factor


def shell_damage(shell, tank):
    '''return health damage'''
    pessimistic_tank = copy(tank)
    pessimistic_tank.width *= 1.1
    pessimistic_tank.height *= 1.1
    front, right, back, left = utils.get_borders(pessimistic_tank)
    # front, right, back, left = utils.get_borders(tank)

    next_shell_x = shell.x + shell.speedX * 1000.
    next_shell_y = shell.y + shell.speedY * 1000.

    borders_with_intersections = [(b,
            geometry.intervals_intersection(
                    b[0], b[1], b[2], b[3], shell.x, shell.y, next_shell_x, next_shell_y)) for
            b in front, right, back, left]

    borders_with_intersections = filter(lambda bi: bi[1] is not None, borders_with_intersections)
    if not borders_with_intersections:
        return 0.
    border, intersection_point = min(borders_with_intersections,
            key=lambda b: math.hypot(b[1][0] - shell.x, b[1][1] - shell.y))

    angle = geometry.get_angle(border[0] - border[2], border[1] - border[3], shell.speedX, shell.speedY)
    if angle > math.pi / 2:
        angle = math.pi - angle
    angle = math.pi / 2. - angle

    r1 = math.hypot(border[0] - intersection_point[0], border[1] - intersection_point[1])
    r2 = math.hypot(border[2] - intersection_point[0], border[3] - intersection_point[1])
    r = r1 + r2
    dist_factor = (r - 2. * min(r1, r2)) / r

    return coeff_by_angle(shell, angle) * coeff_by_dist_factor(dist_factor)
