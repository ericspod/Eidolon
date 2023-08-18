# Eidolon Biomedical Framework
# Copyright (C) 2016-20 Eric Kerfoot, King's College London, all rights reserved
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

import logging
import os
import platform
import subprocess
import sys
import threading
import time
from enum import Enum
from pathlib import Path

from .path_utils import ensure_ext

__all__ = ["is_interactive", "PlatformName", "is_darwin", "is_linux", "is_windows"]

is_darwin = platform.system().lower() == "darwin"
is_windows = platform.system().lower() == "windows"
is_linux = platform.system().lower() == "linux"


class PlatformName(Enum):
    WINDOWS = "windows", is_windows
    LINUX = "linux", is_linux
    DARWIN = "darwin", is_darwin


def is_interactive() -> bool:
    # try:
    #     import __main__
    #     return not hasattr(__main__, "__file__")
    # except ImportError:
    #     return False

    return hasattr(sys, "ps1")


def add_path_variable(varname, path, append=True):
    """
    Add the string `path` to the environment variable `varname` by appending (if `append` is True) or prepending `path`
    using os.pathsep as the separator. This assumes `varname` is a path variable like PATH. Blank paths present in the
    original variable are moved to the end to prevent consecutive os.pathsep characters appearing in the variable. If
    `varname` does not name a variable with text it will be set to `path`.
    """
    var = os.environ.get(varname, "").strip()

    if var:  # if the variable exists and has text
        paths = [p.strip() for p in var.split(os.pathsep)]  # split by the separator and strip whitespace just in case
        paths.insert(len(paths) if append else 0, path)  # append or prepend `path'

        if "" in paths:  # need to move the blank path to the end to prevent :: from appearing in the variable
            paths = list(filter(bool, paths)) + [""]
    else:
        paths = [path]  # variable is new so only text is `path'

    os.environ[varname] = os.pathsep.join(paths)


def set_trace():
    """Enables tracing for the calling thread. This behaviour is unreliable and spews to logs or stdout."""

    def trace(frame, event, arg):
        try:
            filename = frame.f_code.co_filename
            threadname = threading.current_thread().name

            if "threading" in filename:  # ignore thread code tracing
                return None

            if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                logging.debug("%s:%s:%d: %s", threadname, filename, frame.f_lineno, event)
            else:
                print("%s:%s:%d: %s" % (threadname, filename, frame.f_lineno, event), flush=True)
        except:
            pass  # modules get nullified at shutdown so suppress that exception

        return trace

    sys.settrace(trace)


def set_logging(logfile=None, filemode="a", level=logging.DEBUG):
    """
    Enables logging to the given file, or the default log file is not given, with the given filemode and log level.
    Returns the log file path.
    """

    if logfile is None:
        from ..__init__ import APPDATADIR, LOGFILE

        datadir = Path(APPDATADIR).expanduser()
        logfile = str(datadir / LOGFILE)

    logging.basicConfig(
        format="%(asctime)s %(message)s", filename=logfile, filemode=filemode, level=level, datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger().setLevel(level)
    logging.info("Start log")
    logging.raiseExceptions = False  # stop exception prints about the log file being closed when writing traces

    return logfile


def process_exists(pid):
    """
    Returns true if the process identified by `pid' is running and active, false if it doesn't exist or has crashed.
    """
    if is_windows:  # adapted from http://www.madebuild.org/blog/?p=30
        _PROCESS_QUERY_INFORMATION = 1024  # OpenProcess requires this access rights specifier
        _STILL_ACTIVE = 259  # GetExitCodeProcess uses a special exit code to indicate the process is still running

        import ctypes
        import ctypes.wintypes

        kernel32 = ctypes.windll.kernel32

        handle = kernel32.OpenProcess(_PROCESS_QUERY_INFORMATION, 0, pid)
        if handle == 0:
            return False

        # If the process exited recently, a handle may still exist for the pid. So, check if we can get the exit code.
        exitcode = ctypes.wintypes.DWORD()
        result = kernel32.GetExitCodeProcess(handle, ctypes.byref(exitcode))  # returns 0 if failed
        kernel32.CloseHandle(handle)

        # See if we couldn't get the exit code or the exit code indicates that the process is still running.
        return result != 0 and exitcode.value == _STILL_ACTIVE
    else:  # non-Windows platforms, kill is supported in Windows but doesn't detect crashed processes correctly
        try:
            os.kill(pid, 0)  # signal 0 does nothing but still raises an exception if the process doesn't exist
            return True
        except OSError:
            return False


def get_username():
    """Returns the username in a portable and secure way which works with 'su' and non-terminal processes."""
    if is_windows:
        import win32api
        import win32con

        hostuname = win32api.GetUserNameEx(win32con.NameSamCompatible)
        return str(hostuname.split("\\")[-1])
    else:
        import pwd

        return pwd.getpwuid(os.getuid()).pw_name


def exec_batch_program(exefile, *exeargs, timeout=None, cwd=None, env=None, logcmd=False, logfile=None):
    """
    Executes the program `exefile` with the string arguments `exeargs` as a batch process. The return result is a return
    code and output string pair. The integer return code is taken from the program, in the usual case 0 indicating a
    correct execution and any other value indicating failure, and the output is a string of the merged stdout
    and stderr text. If the program requires input it will deadlock, this is a batch operation routine only.

    The keyword value `timeout` can indicates how long to wait for the program in seconds before killing it, this
    routine waits forever if not given. If `logcmd` is True the command line to be executed is printed to stdout before
    being run. If a log file path is given in `logfile`, the output from the program will be piped to that file. An
    environment map can be provided as `env` which will override the inherited environment during the execution.
    """

    exefile = os.path.abspath(exefile)
    output = ""
    errcode = 0

    if is_windows:
        exefile = ensure_ext(exefile, ".exe")

    if logcmd:
        print(exefile, exeargs, f"cwd={cwd} env={env} timeout={timeout} logfile={logfile}", flush=True)

    if not os.path.isfile(exefile):
        raise IOError("Cannot find program %r" % exefile)

    # if log file given, open it to receive output, otherwise send output to pipe
    if logfile is not None:
        stdout = open(logfile, "w+")
    else:
        stdout = subprocess.PIPE

    if env is not None:  # override the environment sent to the process if anything was given
        origenv = dict(os.environ)
        origenv.update(env)
        env = origenv

    proc = subprocess.Popen([exefile] + list(exeargs), stderr=subprocess.STDOUT, stdout=stdout, cwd=cwd, env=env)

    # if timeout is present, kill the process and throw an exception if the program doesn't finish beforehand
    if timeout is not None and timeout > 0:
        tm = float(timeout)
        lasttime = time.time()
        while proc.poll() is None and tm > 0:
            curtime = time.time()
            tm -= curtime - lasttime
            lasttime = curtime
            time.sleep(0.01)

        if tm <= 0:
            proc.kill()
            output = "Process %r failed to complete after %.3f seconds\n" % (exefile, timeout)
            errcode = 1

    out, _ = proc.communicate()

    if errcode != 0 and proc.returncode == 0:  # choose errcode if the process was killed
        returncode = errcode
    else:
        returncode = proc.returncode

    if logfile is not None:  # if a log file was specified, read it into `out' since it will be empty in this case
        stdout.seek(0)
        out = stdout.read()
        stdout.close()

    try:
        out = out.decode("utf-8")
    except:
        pass

    return returncode, output + (out or "")
