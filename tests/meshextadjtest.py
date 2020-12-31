import timeit
import numpy as np

from eidolon.mathdef import ElemType
from eidolon.mathdef.mesh_algorithms import calculate_shared_nodes, calculate_expanded_face_inds, calculate_leaf_ext_adj

cuboid = np.load("data/cuboid.npz")

t = cuboid["t"]

print(t.shape)

et = ElemType.Hex1NL
face_inds = np.array(et.faces)[:, :-1]

# leafdata = np.arange(t.shape[0])
leafdata=np.arange(100000)

num_faces = face_inds.shape[0]
face_size = face_inds.shape[1]
number=10

topo_ext_adj = -np.ones((t.shape[0], et.num_faces * 2), dtype=int)

expanded_face_inds = np.zeros((leafdata.shape[0], num_faces, face_size), dtype=int)

func=lambda: calculate_shared_nodes(t,leafdata)

func()

res=timeit.timeit(func,number=number)

print("calculate_shared_nodes", res/number)

func=lambda: calculate_expanded_face_inds(expanded_face_inds, t, leafdata, face_inds)

func()

res = timeit.timeit(func,number=number)

print("calculate_expanded_face_inds",res/number)

expanded_face_inds = np.sort(expanded_face_inds, axis=2)

func=lambda: calculate_leaf_ext_adj(expanded_face_inds, t, leafdata, face_inds, topo_ext_adj)

func()

res = timeit.timeit(func,number=number)

print("calculate_leaf_ext_adj",res/number)