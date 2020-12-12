import numpy as np
from eidolon.mathdef import vec3, rotator, transform

v = vec3(1, -2, 3)
print(v)
print(tuple(v))
print(v, v.inv(), v.cross(vec3(1, -2, 0)))
print(abs(v))
print(2.1 * (v + 1))
print(list(v))
print((v + 1) == vec3(2, -1, 4), (v + 1) > v)

print(vec3(0, 0, 0).in_aabb(vec3(-1, -1, -1), vec3(1, 1, 1)))
print(vec3.X)

print(~rotator(1, 0, 1, 1))
print(rotator(1, 0, 1, 1).yaw())

print(rotator.from_axis(vec3.X, 0.5).to_matrix())

print(transform(vec3(1, 2, 3), vec3(1, 2, 3), rotator.from_axis(vec3.one, 0.5)).to_matrix())

t1 = transform(vec3(1, 2, -3), vec3(1.1, 1.2, 1.3), rotator.from_axis(vec3.one, 0.5))

m1 = t1.to_matrix()
m2 = (~t1).to_matrix()

print(m1)
print(m2)
print(np.matmul(m1, m2))
