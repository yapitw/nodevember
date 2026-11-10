"""Tutorial figure: what PA_Finger builds, seen from the side, for the raised index and a curled middle finger.

  uv run --with matplotlib python tutorial/src/finger_chain.py tutorial/images/finger-chain.png

The same arithmetic as PA_Finger, PA_Bone and PA_Knuckle in build.py, in the finger's own plane: Up is drawn
upwards and Fwd (towards the palm) to the right. Grey circles: the 44 spheres per bone (radius × 0.88, the oval
section seen edge on); dots and lines: joints and bones; orange: the knuckle spheres.
"""
import math
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle

FINGERS = {     # from build.py: bone lengths, curls (rad), radius at knuckle / tip
    'index: pointing up': ((4.0, 2.3, 1.75), (-0.06, 0.10, 0.07), (1.22, 1.0)),
    'middle: curled': ((4.3, 2.7, 1.9), (1.5, 1.7, 1.05), (1.2, 0.97)),
}


def mix(a, b, t):
    return a + (b - a) * t


def finger(L, C, R01):
    up, fwd = (0.0, 1.0), (1.0, 0.0)
    along = lambda a: (up[0] * math.cos(a) + fwd[0] * math.sin(a), up[1] * math.cos(a) + fwd[1] * math.sin(a))
    palm = lambda a: (fwd[0] * math.cos(a) - up[0] * math.sin(a), fwd[1] * math.cos(a) - up[1] * math.sin(a))
    A = [0.0, C[0], C[0] + C[1], C[0] + C[1] + C[2]]
    J = [(0.0, 0.0)]
    for k in (1, 2, 3):
        d = along(A[k])
        J.append((J[-1][0] + d[0] * L[k - 1], J[-1][1] + d[1] * L[k - 1]))
    R = [R01[0], mix(*R01, 0.45), mix(*R01, 0.75), R01[1]]
    spheres = []
    for k in (1, 2, 3):
        for i in range(44):
            t = i / 43
            mid = math.sin(math.pi * t)
            r = mix(R[k - 1], R[k], t) * (1 - 0.07 * mid)
            p = palm(A[k])
            x = mix(J[k - 1][0], J[k][0], t) + p[0] * 0.12 * r * mid
            y = mix(J[k - 1][1], J[k][1], t) + p[1] * 0.12 * r * mid
            spheres.append((x, y, r * 0.88))
    knuckles = []
    for k in (0, 1, 2):
        flex = min(max(A[k + 1] - A[k], 0.0), 1.3)
        bis = (A[k] + A[k + 1]) * 0.5
        out = R[k] * (0.25 + 0.22 * flex)
        p = palm(bis)
        knuckles.append((J[k][0] - p[0] * out, J[k][1] - p[1] * out, R[k] * 0.6, flex))
    return J, A, spheres, knuckles


data = {name: finger(*v) for name, v in FINGERS.items()}
xs_all = [x + s * r for J, A, sp, kn in data.values() for x, y, r in sp + [k[:3] for k in kn] for s in (-1, 1)]
ys_all = [y + s * r for J, A, sp, kn in data.values() for x, y, r in sp + [k[:3] for k in kn] for s in (-1, 1)]
x0, x1, y0, y1 = min(xs_all) - 2.2, max(xs_all) + 0.8, min(ys_all) - 1.2, max(ys_all) + 0.4
fig, axes = plt.subplots(1, 2, figsize=(10, 6.6), dpi=160)
for ax, (name, (L, C, R01)) in zip(axes, FINGERS.items()):
    J, A, spheres, knuckles = data[name]
    for x, y, r in spheres:
        ax.add_patch(Circle((x, y), r, fill=False, lw=0.35, color='#8a8a8a', alpha=0.55))
    for k, (x, y, r, flex) in enumerate(knuckles):
        ax.add_patch(Circle((x, y), r, fill=True, lw=1.2, ec='#d9822b', fc='#d9822b', alpha=0.28))
        dx, dy = x - J[k][0], y - J[k][1]
        n = math.hypot(dx, dy) or 1.0
        lx, ly = x + dx / n * (r + 0.15), y + dy / n * (r + 0.15)
        ax.text(lx, ly, f'knuckle {k}\nflex {flex:.2f}', ha='left' if dx > 0.05 else 'right', va='center', fontsize=8, color='#b5651d')
    xs, ys = zip(*J)
    ax.plot(xs, ys, '-', color='#2b5d9c', lw=2.2)
    ax.plot(xs, ys, 'o', color='#2b5d9c', ms=6)
    for k, (x, y) in enumerate(J):
        ax.text(x + 0.18, y + 0.05, 'Base' if k == 0 else f'joint {k}', fontsize=8.5, color='#2b5d9c')
    # curl of each bone, measured from the previous bone's direction
    for k in (1, 2, 3):
        x, y = J[k - 1]
        a0, a1 = A[k - 1], A[k]
        if abs(a1 - a0) > 0.2:
            th0, th1 = 90 - math.degrees(a1), 90 - math.degrees(a0)
            ax.add_patch(Arc((x, y), 1.6, 1.6, theta1=min(th0, th1), theta2=max(th0, th1), color='#3a8f5c', lw=1.4))
            ax.text(x + 0.9 * math.sin((a0 + a1) / 2) + 0.15, y + 0.9 * math.cos((a0 + a1) / 2), f'C{k} {C[k - 1]:.2f}',
                    fontsize=8.5, color='#3a8f5c')
    ax.annotate('', xy=(x0 + 0.3, y0 + 1.9), xytext=(x0 + 0.3, y0 + 0.3), arrowprops=dict(arrowstyle='->', color='#555'))
    ax.text(x0 + 0.35, y0 + 1.95, 'Up', fontsize=8, color='#555')
    ax.annotate('', xy=(x0 + 1.9, y0 + 0.3), xytext=(x0 + 0.3, y0 + 0.3), arrowprops=dict(arrowstyle='->', color='#555'))
    ax.text(x0 + 1.95, y0 + 0.3, 'Fwd (palm side)', fontsize=8, color='#555', va='center')
    ax.set_title(name + f'\nL = {L}   C = {C}   R = {R01}', fontsize=9.5)
    ax.set_aspect('equal')
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.axis('off')
fig.suptitle('PA_Finger: three bones, three curls, 44 spheres per bone, a knuckle where a joint bends (units: life-size cm)',
             fontsize=10, y=0.985)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(sys.argv[1], facecolor='white')
print('WROTE', sys.argv[1])
