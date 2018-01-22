
# pylint cleanup stuff
mgr=mgr # pylint:disable=invalid-name,used-before-assignment
scriptdir=scriptdir # pylint:disable=invalid-name,used-before-assignment

import os
import sys
import unittest
import glob

try:
    from StringIO import StringIO
except:
    from io import BytesIO as StringIO

sys.path.append(scriptdir) 

# collect unit test script files and plugin source files which may contain unit tests
srcfiles=glob.glob(os.path.join(scriptdir,'unittests','test*.py'))+glob.glob(os.path.join(scriptdir,'..','src','plugins','*.py'))

totalruns=0
failures=0
errors=0
try:
    out=StringIO()
    sys.stdout=sys.stderr=out # redirect stdout/stderr to the StringIO object out
    
    for src in sorted(srcfiles):
        pdir=os.path.basename(os.path.dirname(src))
        name=os.path.basename(src[:-3])
        suites=unittest.defaultTestLoader.loadTestsFromName('%s.%s'%(pdir,name))
        
        if suites.countTestCases()>0:
            out.write('====================\n'+name+'\n====================\n')
            result=unittest.TextTestRunner(stream=out,verbosity=2).run(suites)
            totalruns+=result.testsRun
            failures+=len(result.failures)
            errors+=len(result.errors)
            out.write('\n\n')
        
finally:
    # restore streams
    sys.stdout=sys.__stdout__
    sys.stderr=sys.__stderr__

resultstr='Unittest results: %i tests run, %i failures, %i errors'%(totalruns,failures,errors)
output=out.getvalue()
print('%s:\n%s'%(resultstr,output))

mgr.showTextBox(resultstr,'Results',output,height=600,width=800)
