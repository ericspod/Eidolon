
import os
import sys
import pytest
import glob

sys.path.append(scriptdir) # used by test scripts to import TestUtils

pytest.main(glob.glob(os.path.join(scriptdir,'unittests','*.py')))
#pytest.main(glob.glob(os.path.join(scriptdir,'..','src','plugins','*.py')))
