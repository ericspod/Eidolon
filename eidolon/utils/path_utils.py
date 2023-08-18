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

import os
import re
import shutil
import time

__all__ = [
    "split_path_ext",
    "get_win_drives",
    "check_valid_path",
    "get_valid_filename",
    "has_ext",
    "ensure_ext",
    "time_backup_file",
    "is_same_file",
    "is_text_file",
    "copy_file_safe",
    "rename_file",
]


def split_path_ext(path, full_ext=False):
    """
    For the given path, return the containing directory, filename without extension, and extension. If `full_ext` is
    True, consider everything to the right of the first period as the extension rather than from the last. For example,
    split_path_ext('foo.bar.baz')[2] produces '.baz' whereas split_path_ext('foo.bar.baz',True)[2] produces '.bar.baz'.
    """
    path, basename = os.path.split(path)

    if full_ext and "." in basename:
        basename, ext = basename.split(".", 1)  # consider everything to the right of the first . as the extension
        ext = "." + ext
    else:
        basename, ext = os.path.splitext(basename)  # consider everything to the right of the last . as the extension

    return path, basename, ext


def get_win_drives():
    """Returns available Windows drive letters."""
    import win32api

    d = win32api.GetLogicalDriveStrings()
    return [dd[0] for dd in d.split("\x00") if dd]


def check_valid_path(path):
    """
    Returns values to indicate if `path' is a valid pathname and if not why. This will return 0 if `path` exists or
    otherwise is a valid path, 1 if not accessible, 2 if the filename component contains invalid characters, and 3 if
    the extension contains invalid characters.
    """
    pdir, basename, ext = split_path_ext(path)
    invalidchars = "\\/:;*?!<>|\"'\0"

    if os.path.exists(path):
        return 0
    elif not os.access(pdir, os.W_OK):
        return 1
    elif any(i in basename for i in invalidchars):
        return 2
    elif any(i in ext for i in invalidchars):
        return 3

    return 0


def get_valid_filename(name):
    """Replaces all invalid filename characters with underscore."""
    return re.sub(r"[.\s<>?:;!*/|%\'\"\[\]]", "_", name)


def has_ext(path, *exts):
    """Returns True if the filename `path` has any of the extensions in `exts`, which can start with a period or not."""
    return any(path.endswith(("" if e[0] == "." else ".") + e) for e in exts)


def ensure_ext(path, ext, replace_ext=False):
    """
    Ensures the returned path ends with extension `ext`. If the path doesn't have `ext` as its extension, this returns
    `path` with `ext` appended, replacing any existing extension if `replace_ext` is True. Eg. ensure_ext('foo','.bar')
    returns 'foo.bar' as does ensure_ext('foo.baz','.bar',True), but ensure_ext('foo.baz','.bar') returns 'foo.baz.bar'.
    """
    namepart, extpart = os.path.splitext(path)
    if namepart and extpart != ext:
        path = (namepart if replace_ext else path) + ext

    return path


def time_backup_file(filename, back_dir=None):
    """
    Copies `filename' if it exists to the same directory (or `backDir' if not None) with the system time and ".old"
    appended to the name. The new base filename is returned if this was done, otherwise None.
    """
    if os.path.exists(filename):
        root, name = os.path.split(filename)
        back_dir = back_dir or root
        timefile = "%s.%s.old" % (name, time.time())
        shutil.copyfile(filename, os.path.join(back_dir, timefile))
        return timefile


def is_same_file(src, dst):
    """Returns True if the files `src` and `dst` refer to the same extant file."""
    if not os.path.exists(src) or not os.path.exists(dst):
        return False

    if hasattr(os.path, "samefile") and os.path.samefile(src, dst):
        return True

    if os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dst)):
        return True

    return False


def is_text_file(filename, bufferlen=512):
    """Checks the first `bufferlen` characters in `filename` to assess whether the file is a text file or not."""
    buf = open(filename).read(bufferlen)
    return "\0" not in buf  # FIXME: maybe something a bit more involved than just checking for null characters?


def copy_file_safe(src, dst, overwrite_file=False):
    """
    Copy file from path `src` to path `dst` only if they are not the same file. If `overwrite_file` is True, raise an
    IOError if `dst` already exists.
    """
    if not is_same_file(src, dst):
        if not overwrite_file and os.path.exists(dst):
            raise IOError(f"File already exists: {dst}")

        shutil.copyfile(src, dst)


def rename_file(oldpath, newname, move_file=True, overwrite_file=False):
    """
    Replace the basename without extension in `oldpath` with `newname` and keeping the old extension. If `move_file` is
    True, move the old file to the new location and overwrite existing file if `overwrite_file` is True. IOError
    is raised if this isn't possible or if the file exists and `overwrite_file` is False. Setting `move_file` to False
    allows a "dry run" where the checks are performed but the file isn't moved. Returns the new path.
    Eg. rename_file('/foo/bar.baz.plonk','thunk') -> '/foo/thunk.baz.plonk'
    """
    olddir, oldname, ext = split_path_ext(oldpath, True)
    newpath = os.path.join(olddir, newname + ext)

    if not os.path.exists(oldpath):
        raise IOError("Cannot move %r to %r, source file does not exist" % (oldpath, newpath))
    elif os.path.exists(newpath) and not overwrite_file:
        raise IOError("Cannot move %r to %r, destination file already exists" % (oldpath, newpath))
    elif is_same_file(oldpath, newpath):
        raise IOError("File names %r and %r refer to the same file" % (oldpath, newpath))
    elif move_file:
        shutil.move(oldpath, newpath)

    return newpath
