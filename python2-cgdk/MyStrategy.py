import math
from model.FireType import FireType
from model.TankType import TankType
from model.ShellType import ShellType
from model.BonusType import BonusType
from model.Unit import Unit

SHELL_AVERAGE_SPEED = 14.7
TANK_AVERAGE_SPEED = 1.5
SHELL_WIDTH = 22.5
SHELL_HEIGHT = 7.5

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


def get_max_premium_distance(world):
    return math.hypot(world.width, world.height) / 2


def rad_to_degree(rad):
    return (rad * 180) / math.pi


def degree_to_rad(degree):
    return (degree * math.pi) / 180


def get_cross(v1x, v1y, v2x, v2y):
    return v1x * v2y - v1y * v2x


def get_cross_sign(v1x, v1y, v2x, v2y):
    cc = get_cross(v1x, v1y, v2x, v2y)
    return 1. if cc > 0 else -1.


def are_intervals_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    a1 = x2 - x1
    a2 = y2 - y1
    b1 = x3 - x4
    b2 = y3 - y4
    c1 = x3 - x1
    c2 = y3 - y1
    d = float(a1 * b2 - a2 * b1)

    if abs(d) < 0.001:
        return False

    t = (c1 * b2 - c2 * b1) / d
    s = (c2 * a1 - c1 * a2) / d

    return 0 <= t <= 1 and 0 <= s <= 1


# for aa, correct in [
#         ((0, 0, 0, 1, 0, 0, 1, 0), True),
#         ((0, 0.5, 0, 1, 0.5, 0, 1, 0), False),
#         ((0, 1, 1, 0, 0, 0, 1, 1), True),
#         ((0, 1, 0.25, 0.75, 0, 0, 1, 1), False),
#         ((0, 0, 1, 1, 0, 1, 1, 1.0004), False),
#         ((0, 0, 1, 1, 0, 1, 1, 0.999), True),
#         ((0, 0, 1, 1, 0, 1, 0.99, 1), False),
#         ((0, 0, 0, 1, 1, 0, 1, 1), False),
#         ]:
#     ans = are_intervals_intersect(*aa)
#     if ans != correct:
#         print "error !!!"
#     print aa, ans

def get_nearest_point(bx, by, ex, ey, px, py):
    ebx = bx - ex
    eby = by - ey
    l_eb = math.hypot(ebx, eby)

    nebx = ebx / l_eb
    neby = eby / l_eb

    epx = px - ex
    epy = py - ey

    l_ep = math.hypot(epx, epy)

    angle = get_angle(ebx, eby, epx, epy)

    nx = ex + nebx * math.cos(angle) * l_ep
    ny = ey + neby * math.cos(angle) * l_ep

    return nx, ny


def get_angle(v1x, v1y, v2x, v2y):
    l1 = math.hypot(v1x, v1y)
    l2 = math.hypot(v2x, v2y)
    prod = (v1x * v2x + v1y * v2y) / (l1 * l2)
    if prod < -1:
        prod = -1
    if prod > 1:
        prod = 1
    return math.acos(prod)


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
    # FIXME add check if enemy blocked
    if me.get_distance_to_unit(enemy) < get_max_premium_distance(world) and \
            me.premium_shell_count > 0:
        return possible_premium_score(me, enemy, world)
    return possible_usual_score(me, enemy, world)


def get_target_enemy(me, world):
    enemies = all_enemies(world)
    # return min(enemies, key=lambda t: time_before_hit(me, t))
    return max(enemies, key=lambda e: possible_score(me, e, world) / time_before_hit(tank=me, target=e))


def is_goal_blocked_by(shell, goal, blocker):
    borders = get_borders(blocker)

    vx = goal.x - shell.x
    vy = goal.y - shell.y
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

    # m_dist = me.get_distance_to_unit(blocker)
    # g_dist = blocker.get_distance_to_unit(goal)
    # dist = me.get_distance_to_unit(goal)

    # size = math.hypot(blocker.width, blocker.height)

    # v1x = me.x - blocker.x
    # v1y = me.y - blocker.y

    # v2x = goal.x - blocker.x
    # v2y = goal.y - blocker.y

    # angle = get_angle(v1x, v1y, v2x, v2y)
    # if angle < math.pi / 2:
    #     return False

    # h = (m_dist * g_dist * math.sin(angle)) / dist
    # return h < size / 2


def is_goal_blocked(shell, goal, world):
    blockers = world.bonuses + filter(lambda t: not alive(t), world.tanks)

    # check for the same units
    blockers = filter(lambda o: o.get_distance_to_unit(shell) > 0.01 and
            o.get_distance_to_unit(goal) > 0.01, blockers)

    for blocker in blockers:
        if is_goal_blocked_by(shell, goal, blocker):
            return True
    return False


def fire_to(goal, me, world, move):

    distance = me.get_distance_to_unit(goal)
    # FIXME add something clever here
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

    tvx = math.cos(me.angle + me.turret_relative_angle)
    tvy = math.sin(me.angle + me.turret_relative_angle)
    possible_shell = Unit(0, width=SHELL_WIDTH, height=SHELL_HEIGHT,
            x=me.x, y=me.y,
            speed_x=tvx * SHELL_AVERAGE_SPEED,
            speed_y=tvy * SHELL_AVERAGE_SPEED,
            angle=me.angle + me.turret_relative_angle, angular_speed=0)

    if abs(turret_angle) > max_fire_angle:
        move.fire_type = FireType.NONE
    elif is_goal_blocked(possible_shell, goal, world):
        move.fire_type = FireType.NONE
    else:
        if distance > get_max_premium_distance(world):
            move.fire_type = FireType.REGULAR
        else:
            move.fire_type = FireType.PREMIUM_PREFERRED


def move_to_unit(goal, me, world, move):
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

    if not is_goal_blocked_by(shell, next_shell, me):
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


def get_strategic_goal(me, world):
    enemies = all_enemies(world)

    if len(enemies) <= 1:
        if len(world.bonuses) > 0:
            goal = max(world.bonuses, key=lambda b: get_bonus_rating(me, b))
            return Point(goal.x, goal.y)

        return Point(world.width / 2, world.height / 2)

    if len(world.bonuses) > 0:
        goal = max(world.bonuses, key=lambda b: get_bonus_rating(me, b))
        min_enemy_dist = min([me.get_distance_to_unit(e) for e in (enemies)])
        if me.get_distance_to_unit(goal) < min_enemy_dist:
            return Point(goal.x, goal.y)

    delta = 60
    corners = [
        Point(delta, delta),
        Point(world.width - delta, delta),
        Point(world.width - delta, world.height - delta),
        Point(delta, world.height - delta)
        ]

    return min(corners, key=lambda c: me.get_distance_to_unit(c))


def enemy_is_going_hit_only_me(me, enemy, enemies):
    mine_time = time_before_hit(tank=enemy, target=me)
    for other_enemy in enemies:
        if other_enemy.id == enemy.id:
            continue
        if time_before_hit(tank=enemy, target=other_enemy) < mine_time:
            return False
    return True


def avoid_possible_shells(me, world, move):
    enemies = all_enemies(world)
    if len(enemies) == 0:
        return False

    dangerous_enemies = filter(lambda e: enemy_is_going_hit_only_me(me, e, enemies), enemies)
    very_dangerous_enemies = filter(lambda e: time_before_hit(tank=e, target=me) <= 100, dangerous_enemies)
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

    # log_print('avoid possible shell')
    return avoid_shell(possible_shell, me, world, move)


class MyStrategy:
    def __init__(self):
        self.counter = 0

    def move(self, me, world, move):

        target_enemy = get_target_enemy(me, world)

        fire_to(target_enemy, me, world, move)

        if not avoid_shells(me, world, move):
            if not avoid_possible_shells(me, world, move):
                stratgic_goal = get_strategic_goal(me, world)
                move_to_unit(stratgic_goal, me, world, move)

        self.counter += 1

    def select_tank(self, tank_index, team_size):
        return TankType.MEDIUM