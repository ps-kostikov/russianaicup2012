import math

from model.ShellType import ShellType
from model.Unit import Unit
from model.Tank import Tank
from model.Shell import Shell

import geometry
import utils
import assessments

REGULAR_COEFF = 0.995
PREMIUM_COEFF = 0.99


def next_shell(shell, world):
	new_x = shell.x + shell.speedX
	new_y = shell.y + shell.speedY
	if shell.type == ShellType.REGULAR:
		new_speed_x = shell.speedX * REGULAR_COEFF
		new_speed_y = shell.speedY * REGULAR_COEFF
	else:
		new_speed_x = shell.speedX * PREMIUM_COEFF
		new_speed_y = shell.speedY * PREMIUM_COEFF

	new_shell = Shell(id=shell.id, player_name=shell.player_name, width=shell.width, height=shell.height,
			x=new_x,
			y=new_y,
			speed_x=new_speed_x,
			speed_y=new_speed_y,
			angle=shell.angle, angular_speed=shell.angular_speed, type=shell.type)
	return new_shell


def next_tank(tank, world, move_left, move_right):
    if move_left < 0:
        move_left *= 0.75

    if move_right < 0:
        move_right *= 0.75

    a = 0.1
    nsx = tank.speedX + a * (move_right + move_left) * math.cos(tank.angle)
    nsy = tank.speedY + a * (move_right + move_left) * math.sin(tank.angle)

    nx = tank.x + nsx
    ny = tank.y + nsy

    angle_a = 0.000627876445651 / 1.5
    nsa = tank.angular_speed + angle_a * (move_right - move_left)
    na = tank.angle + nsa
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
        shell_prev = shell_next
        tank_prev = tank_next
        dist_prev = dist_next

        tank_next = next_tank(tank_prev, world, move_left, move_right)
        shell_next = next_shell(shell_prev, world)
        dist_next = tank_next.get_distance_to_unit(shell_next)

        if touch_next_tick(shell, shell_next, tank_next):
            return assessments.shell_damage(shell, tank_next)

    return 0.