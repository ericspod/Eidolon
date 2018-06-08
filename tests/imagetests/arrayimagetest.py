# Eidolon Biomedical Framework
# Copyright (C) 2016-8 Eric Kerfoot, King's College London, all rights reserved
# 
# This file is part of Eidolon.
#
# Eidolon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Eidolon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program (LICENSE.txt).  If not, see <http://www.gnu.org/licenses/>

from eidolon import *
import numpy as np

w=11
h=13
d=17
t=5

# construct an array with unique incrementing values in incrementing indices
arr=np.fromfunction(lambda i,j,k,l:i+(j*w)+(k*w*h)+(l*w*h*d),(w,h,d,t))

assert arr[0,0,0,0]==0
assert arr[w-1,0,0,0]==w-1
assert arr[w-1,1,0,0]==w-1+w

o=ImgPlugin.createObjectFromArray('arraytest',arr)
mgr.addSceneObject(o)

assert o.images[0].img[0,0]==0
assert o.images[0].img[0,w-1]==w-1
assert o.images[0].img[1,w-1]==w-1+w

with processImageNp(o) as mat: # check the original and reproduced arrays are identical
    assert arr.ndim==mat.ndim
    assert all(s1==s2 for s1,s2 in zip(mat.shape,arr.shape))
    assert np.all(arr==mat)

    
rep=o.createRepr(ReprType._imgtimestack)
mgr.addSceneObjectRepr(rep)

mgr.setCameraSeeAll()
