# Eidolon Biomedical Framework
# Copyright (C) 2016-7 Eric Kerfoot, King's College London, all rights reserved
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

# Run unit tests from this directory with the command "../../run.sh *tests.py"

import math
from nose.tools import eq_
from random import triangular


epsilon=1e-10 # separate value that can be tweaked for tests only
halfpi=math.pi/2
quartpi=math.pi/4

def neq_(a,b):
    assert a!=b, '%r == %r' % (a, b)
    

def eqa_(a,b):
    assert abs(a-b)<=epsilon, '%r != %r' % (a, b)


def eqas_(a,b):
    assert all(abs(i-j)<=epsilon for i,j in zip(a,b)), '%r != %r' % (a, b)


def randnums(num,minv,maxv):
    return tuple(triangular(minv,maxv) for _ in xrange(num))
    
    
def randangle():
    return triangular(-math.pi*2,math.pi*2)