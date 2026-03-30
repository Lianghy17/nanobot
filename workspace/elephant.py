#!/usr/bin/env python3
"""
使用 matplotlib 绘制大象
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Ellipse, Circle, Arc
from matplotlib.collections import PatchCollection
import matplotlib.patches as mpatches

fig, ax = plt.subplots(figsize=(12, 8))
ax.set_xlim(0, 12)
ax.set_ylim(0, 8)
ax.set_aspect('equal')
ax.axis('off')
fig.patch.set_facecolor('#E0F7FA')

# 绘制大象的各个部分
# 身体（大椭圆）
body = Ellipse((6, 4), 5.5, 3.5, facecolor='#90A4AE', edgecolor='#546E7A', linewidth=2)
ax.add_patch(body)

# 头部（圆形）
head = Circle((3.2, 5), 1.3, facecolor='#90A4AE', edgecolor='#546E7A', linewidth=2)
ax.add_patch(head)

# 眼睛
eye_white = Circle((2.7, 5.3), 0.35, facecolor='white', edgecolor='#546E7A', linewidth=1)
ax.add_patch(eye_white)
eye_pupil = Circle((2.6, 5.2), 0.15, facecolor='#263238', edgecolor='black', linewidth=1)
ax.add_patch(eye_pupil)

# 耳朵（大椭圆）
ear_left = Ellipse((2.5, 4.2), 1.5, 2.2, angle=-15, facecolor='#78909C', edgecolor='#546E7A', linewidth=2)
ax.add_patch(ear_left)

# 象鼻 - 使用参数方程绘制曲线
t = np.linspace(0, np.pi, 100)
x_trunk = 2.5 + 0.4 * t
y_trunk = 4.5 - 0.8 * t + 0.3 * np.sin(t * 3)
ax.fill(x_trunk, y_trunk, color='#90A4AE', edgecolor='#546E7A', linewidth=2)

# 象牙
tusk_x = [2.3, 1.8]
tusk_y = [4.2, 3.5]
ax.plot(tusk_x, tusk_y, color='#FFF8E1', linewidth=6, solid_capstyle='round')
ax.plot(tusk_x, tusk_y, color='#FFE0B2', linewidth=2, solid_capstyle='round')

# 腿部
legs = [
    Ellipse((4.5, 1.5), 1.2, 2.5, facecolor='#90A4AE', edgecolor='#546E7A', linewidth=2),
    Ellipse((6.0, 1.5), 1.2, 2.5, facecolor='#90A4AE', edgecolor='#546E7A', linewidth=2),
    Ellipse((7.5, 1.5), 1.2, 2.5, facecolor='#90A4AE', edgecolor='#546E7A', linewidth=2),
    Ellipse((5.2, 1.5), 1.2, 2.5, facecolor='#90A4AE', edgecolor='#546E7A', linewidth=2)
]
for leg in legs:
    ax.add_patch(leg)

# 脚趾
for lx in [4.5, 6.0, 7.5, 5.2]:
    for dx in [-0.3, 0, 0.3]:
        toe = Circle((lx + dx, 0.7), 0.12, facecolor='#CFD8DC', edgecolor='#546E7A', linewidth=1)
        ax.add_patch(toe)

# 尾巴
tail_x = [8.5, 9.5, 9.8]
tail_y = [4.5, 4.2, 3.0]
ax.plot(tail_x, tail_y, color='#546E7A', linewidth=3)
# 尾巴尖
ax.plot([9.7, 9.9], [3.0, 2.5], color='#546E7A', linewidth=2)
ax.plot([9.8, 9.8], [3.0, 2.5], color='#546E7A', linewidth=2)

# 添加标题
ax.text(6, 7.3, '🐘 大象 Elephant 🐘', ha='center', va='center', 
        fontsize=24, fontweight='bold', color='#37474F')

plt.tight_layout()
plt.savefig('/Users/lianghaoyun/project/nanobot/workspace/elephant.png', dpi=150, bbox_inches='tight', 
            facecolor='#E0F7FA', edgecolor='none')
print("大象绘制完成！已保存到 elephant.png")
plt.show()
