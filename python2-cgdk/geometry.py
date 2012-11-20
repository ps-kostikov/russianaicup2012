'''
Functions related to geometry evaluations
'''

import math


def rad_to_degree(rad):
    return (rad * 180) / math.pi


def degree_to_rad(degree):
    return (degree * math.pi) / 180


cache = {}
def intervals_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
    global cache
    key = ("{0:.2f}" * 8).format(x1, y1, x2, y2, x3, y3, x4, y4)
    if cache.has_key(key):
        return cache[key]

    def do_cache(value):
        cache[key] = value
        return value

    a1 = x2 - x1
    a2 = y2 - y1
    b1 = x3 - x4
    b2 = y3 - y4
    c1 = x3 - x1
    c2 = y3 - y1
    d = float(a1 * b2 - a2 * b1)

    if abs(d) < 0.001:
        return do_cache(None)

    t = (c1 * b2 - c2 * b1) / d
    s = (c2 * a1 - c1 * a2) / d

    if 0 <= t <= 1 and 0 <= s <= 1:
        return do_cache((x2 * t + (1 - t) * x1, y2 * t + (1 - t) * y1))
    return do_cache(None)

def are_intervals_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
    return intervals_intersection(x1, y1, x2, y2, x3, y3, x4, y4) is not None


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
#     print intervals_intersection(*aa)
#     if ans != correct:
#         print "error !!!"
#     print aa, ans

def get_nearest_point(bx, by, ex, ey, px, py):
    if math.hypot(bx - px, by - py) < 0.0001:
        return bx, by
    if math.hypot(ex - px, ey - py) < 0.0001:
        return ex, ey
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
