'''
Approximate functions for value assessments
'''

import math

from model.Tank import Tank

from geometry import *
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

    return min(life, hull) * \
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