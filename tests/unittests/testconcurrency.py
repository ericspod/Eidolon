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


import threading
import multiprocessing
import unittest

from TestUtils import eqas_
import eidolon
from eidolon import ProcessServer, listResults, checkResultMap, listSum
    
    
class TestVec3(unittest.TestCase):    
	def testServer(self):
		'''Test the global ProcessServer instance was created.'''
		serv=ProcessServer.globalServer
		assert serv is not None
		assert serv.realnumprocs>0
	
	def testConcurrency(self,values=range(100),numprocs=0,task=None):
		'''Test concurrent processing on input and returning values.'''
		result=eidolon.concurrencyTestRange(len(values),numprocs,task,values)
		checkResultMap(result)
		eqas_(values,listSum(listResults(result)))
	
	def testProcessValues(self,numvals=100,numprocs=0,task=None):
		'''Test calling the ProcessServer directly with a routine that prints per-process info.'''
		result=ProcessServer.globalServer.callProcessFunc(numvals,numprocs,task,eidolon.concurrencyTestProcessValues)
		checkResultMap(result())
	
	def testReturnArg(self,values=range(20),numprocs=0,task=None):
		'''Test returned values from processes.'''
		result=eidolon.concurrencyTestReturnArg(len(values),numprocs,task,values,partitionArgs=(values,))
		checkResultMap(result)
	
	def testShareObject(self,numprocs=0,task=None):
		'''Test sharing values between processes.'''
		result=eidolon.concurrencyTestShareObjects(100,numprocs,task)
		checkResultMap(result)
		
	def testPipe(self):
		'''Test the asynchronous creation of a Pipe object, this fails with Nose and indicated a thread-unsafe configuration.'''
		result=[]
		def createPipe():
			result.append(multiprocessing.Pipe())
			
		t=threading.Thread(target=createPipe)
		t.start()
		t.join()
		assert len(result)==1
    
