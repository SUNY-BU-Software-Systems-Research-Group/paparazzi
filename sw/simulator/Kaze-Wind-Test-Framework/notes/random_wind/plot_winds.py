import matplotlib.pyplot as plt
import numpy as np
import time


def randrange(n, vmin, vmax):
    return (vmax - vmin) * np.random.rand(n) + vmin

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
max_mag = 10
n = 3000
thetas = 2*np.pi*np.random.rand(n)
vs = np.random.rand(n)
phis = np.arccos((2*vs)-1)
magnitudes = max_mag*np.random.rand(n)
#magnitudes = 1
xs = np.cos(thetas) * np.sin(phis) 
ys = np.sin(phis) * np.sin(thetas) 
zs = np.cos(phis)  

xs = magnitudes*xs
ys = magnitudes*ys
zs = magnitudes*zs
ax.scatter(xs,ys,zs, marker='o')

count = 0

for z in zs:
    pass
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')

plt.show()
