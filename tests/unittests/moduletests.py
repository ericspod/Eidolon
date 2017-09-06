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

import nose
from eidolon import getSceneMgr, asyncfunc,printFlush,timing

    
class TestModules(object):
    def __init__(self):
        pass
    
    @staticmethod
    def addTestFunc(func,args):
        proxy=lambda _:func(*args)
        proxy.__name__='test_'+func.__name__
        proxy.__doc__=func.__doc__
        
        setattr(TestModules,proxy.__name__,proxy)
        del proxy
    

mgr=getSceneMgr()
for pname in mgr.getPluginNames():
    plugin=mgr.getPlugin(pname)

    for testcase in plugin.getTests():
        TestModules.addTestFunc(testcase[0],testcase[1:])    


# @asyncfunc
# @timing
# def _runtests():
#     nose.runmodule()
# 
# _runtests()

nose.runmodule()
