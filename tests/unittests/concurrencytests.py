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

try:
    import sys
    sys.path.append(scriptdir+'..')
except:
    pass # the script is run 2nd time by nose which doesn't have scriptdir in its namespace, this can safely fail silently

import os
import time
import glob
#import nose
import multiprocessing
import threading
from TestUtils import eq_,eqas_
import eidolon
from eidolon import asyncfunc,Future,timing, AlgorithmProcess, ProcessServer, printFlush,listResults, checkResultMap, listSum
    
    
def testServer1():
    serv=ProcessServer.globalServer
    assert serv is not None
    assert serv.realnumprocs>0


def testServer2():    
    result=ProcessServer.globalServer.callProcessFunc(100,1,None,eidolon.concurrencyTest2Range)
    assert result() is not None


def testConcurrency1(values=range(20),numprocs=0,task=None):
    result=eidolon.concurrencyTest1Range(len(values),numprocs,task,values)
    checkResultMap(result)
    eqas_(values,listSum(listResults(result)))
    #printFlush([len(result[i]) for i in sorted(result)])


def testConcurrency2(numvals=100,numprocs=0,task=None):
    result=ProcessServer.globalServer.callProcessFunc(numvals,numprocs,task,eidolon.concurrencyTest2Range)
    checkResultMap(result())
    #printFlush(listResults(result()))


def testConcurrency3(values=range(20),numprocs=0,task=None):
    result=eidolon.concurrencyTest3Range(len(values),numprocs,task,values,partitionArgs=(values,))
    checkResultMap(result)
    #printFlush(listResults(result))
    

#def testRange1():
#    values=range(100)
#    result=concurrencyTest1Range(len(values),0,None,values)
#    #printFlush([len(result[i]) for i in sorted(result)])
#    eq_(values,listResults(result))


#def concurrencyTest2Range(process):
#    return (process.index,os.getpid(),int(process.startval),int(process.endval))
#
#
#def testDirectCall1():
#    result=ProcessServer.globalServer.callProcessFunc(100,1,None,concurrencyTest2Range)
#    checkResultMap(result(1.0))
#    printFlush(listResults(result()))
#    
#
#@concurrent 
#def concurrencyTest3Range(process,values):
#    return (process.index,values)
#
#
#def concurrencyTest3(values=range(20),numprocs=0,task=None):
#    printFlush(values)
#    result=concurrencyTest3Range(len(values),numprocs,task,concurrencyTest3Range,values,partitionArgs=(values,))
#    printFlush(listResults(result))
# 
#
#def testPipe1():
#    result=[]
#    def createPipe():
#        result.append(multiprocessing.Pipe())
#        
#    t=threading.Thread(target=createPipe)
#    t.start()
#    time.sleep(1.0)
#    assert len(result)==1
    

#nose.runmodule() 
