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


import sys
import codeop
import queue
import threading
import time
import traceback
from pathlib import Path

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt

from eidolon.utils import is_darwin, first

try:
    from qtconsole.inprocess import QtInProcessKernelManager, QtInProcessRichJupyterWidget

    jupyter_present = True
except ImportError:
    QtInProcessRichJupyterWidget = QtWidgets.QWidget  # bogus type definition to satisfy inheritance
    jupyter_present = False

__all__ = ["jupyter_present", "JupyterWidget", "ConsoleWidget"]

init_cmd = "from eidolon import ui, renderer, utils"


class JupyterWidget(QtInProcessRichJupyterWidget):
    """
    Jupyter substitute widget for the internal console. This will be used by default if the relevant libraries are
    imported. As a drop-in replacement for ConsoleWidget its public interface is meant to be the same.
    """

    def __init__(self, win, conf, parent=None):
        super().__init__(parent)
        self.win = win
        self.conf = conf

        self.custom_restart = True  # prevent restarting the kernel?

        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel(show_banner=False)
        self.kernel = self.kernel_manager.kernel
        self.kernel.gui = 'qt'

        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        self.setStyleSheet(win.styleSheet())

        self.update_locals({"console": self, "win": self.win})
        self.send_input_block(init_cmd, False)

    def update_locals(self, localvals):
        """Override the local variable dictionary with the given dictionary."""
        self.kernel.shell.push(localvals)

    def send_input_block(self, block, print_block=True):
        """Interpret the given code `block'."""
        return self.execute(block, not print_block)


class ConsoleWidget(QtWidgets.QTextEdit):
    """
    Simulates a Python terminal in a QTextEdit widget. This is similar to code.InteractiveConsole in how it executes
    individual lines of source. It includes a basic session history feature.
    """

    def __init__(self, win, conf, parent=None):
        QtWidgets.QTextEdit.__init__(self, parent)
        self.setFont(QtGui.QFont('Courier', 10))

        self.win = win
        self.logfile = ''
        self.locals = {"console": self, "win": self.win}
        self.comp = codeop.CommandCompiler()
        self.inputlines = queue.Queue()
        self.linebuffer = []
        self.history = []
        self.historypos = 0
        self.curline = ''
        self.is_executing = False
        self.init_cmds = [init_cmd]

        self.is_meta_down = False  # is a meta (shift/ctrl/alt/win/cmd) down?
        self.metakeys = (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_AltGr, Qt.Key_Meta)
        self.metadown = 0

        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr

        try:
            self.ps1 = sys.ps1
        except:
            self.ps1 = '>>> '

        try:
            self.ps2 = sys.ps2
        except:
            self.ps2 = '... '

        self.currentPrompt = self.ps1

        # try to read the setting for number of log file lines, default to 10000 if not present
        self.loglines = int(conf.get("consoleloglen", 10000))

        # try to set the log filename, if there's no user directory this won't be set so no logging will occur
        from eidolon.config import APPDATADIR
        appdatadir = Path(APPDATADIR)
        if appdatadir.is_dir():
            self.logfile = str(appdatadir / conf["consolelogfile"])

        # read the log file
        if Path(self.logfile).is_file():
            try:
                with open(self.logfile) as o:
                    log = [s.rstrip() for s in o.readlines()]

                self.history = log[-self.loglines:]  # add no more than v1.loglines values to the history
            except Exception as e:
                self.write('Cannot open console log file %r:\n%r\n' % (self.logfile, e))

        self.thread = threading.Thread(target=self._interpret_thread)
        self.thread.daemon = True
        self.thread.start()

    def _interpret_thread(self):
        """
        Daemon thread method which prints the appropriate prompt and reads commands given through send_input_line().
        These are then executed with execute().
        """

        # while not v1.win.isExec:
        #     time.sleep(0.01)  # wait for window to appear

        for cmd in self.init_cmds:
            self.execute(cmd)  # execute initialization commands

        self.send_input_line('')  # show initial prompt

        multiline = False  # indicates if following lines are expected to be part of a indented block
        while True:
            line = self.inputlines.get()

            # execute each line in the lines queue, printing the appropriate prompt when the queue is empty
            while line is not None:
                multiline = self.execute(line)

                if self.inputlines.empty():  # no more lines, write prompt and wait
                    self.currentPrompt = self.ps2 if multiline else self.ps1

                    if len(self.get_current_line()) > 0:  # ensure prompt goes onto a new line
                        self.write('\n')

                    self.write(self.currentPrompt)
                    line = None
                else:
                    line = self.inputlines.get(0)

    def send_input_line(self, line, append_history=True):
        """Send the given line to the interpreter's line queue."""

        # skip the usual console exiting commands, these don't make sense for a persistent console
        if line in ('exit', 'exit()', 'quit', 'quit()'):
            inputline = ''  # do nothing, forces clean prompt printing
        else:
            # execute command and append to history
            inputline = line
            self.historypos = 0

            # append only if not a duplicate of previous entry
            if append_history and len(line.strip()) > 0 and (len(self.history) == 0 or self.history[-1] != line):
                self.history.append(line)

                # write to log file if present
                if self.logfile:
                    try:
                        with open(self.logfile, 'a') as o:
                            o.write('%s\n' % line)
                    except Exception as e:
                        self.write('Cannot write to console log file %r:\n%r\n' % (self.logfile, e))

        self.inputlines.put(inputline)

    def send_input_block(self, block, print_block=True):
        """Send a block of code lines `block' to be interpreted, printing the block to the console if `print_block'."""
        block = str(block)
        lines = block.split('\n')

        if len(lines) == 1:  # if there's only one line, print it and wait for user interaction
            self.write(lines[0])
        elif len(lines) > 1:
            if print_block:  # set the cursor and print out the code block into the console
                self._set_cursor(endline=True)
                self.write(block + '\n')

            lastindent = 0  # last line's indent distance
            for line in lines:
                if line.strip():  # skip empty lines
                    indent = first(i for i in range(len(line)) if not line[i].isspace())  # get line's indent
                    # if this line is not indented but last one was, send an empty line to end a multi-line input block
                    if indent == 0 and lastindent > 0:
                        self.send_input_line('\n')

                    lastindent = indent
                    self.send_input_line(line)

            self.send_input_line('\n')

    def update_locals(self, localvals):
        """Override the local variable dictionary with the given dictionary."""
        self.locals.update(localvals)

    def execute(self, line):
        """
        Compile and interpret the given Python statement. Returns true if more statements are expected to fill an
        indented block, false otherwise.
        """

        try:
            # If compiling an indented block (eg. an if statement) all the lines of the block must be submitted at
            # once followed by a blank line. Only then will the compile happen, otherwise a None object is returned
            # indicating more lines are needed. To do this statements accumulate in the buffer until compilation.
            self.linebuffer.append(line)
            comp = self.comp('\n'.join(self.linebuffer), '<console>')

            if comp is None:  # expecting more statements to fill in an indented block, return true to indicate this
                return True

            sys.stdout = self  # reroute stdout/stderr to print to the widget
            sys.stderr = self
            self.linebuffer = []

            self.is_executing = True
            exec(comp, self.locals)  # execute the statement(s) in the context of the local symbol table

        except SyntaxError as se:
            self.linebuffer = []
            self.write('\n'.join(l.rstrip() for l in traceback.format_exception_only(SyntaxError, se) if l.strip()))

        except Exception as e:
            self.linebuffer = []
            self.write(str(e) + '\n')
            self.write(traceback.format_exc())

        finally:
            sys.stdout = self.orig_stdout  # always restore stdout/stderr
            sys.stderr = self.orig_stderr
            self.is_executing = False

        return False  # no more statements expected

    def write(self, line):
        """Write a line of text to the text window."""

        # @v1.win.callFuncUIThread
        # def write_line():
        #     v1.insertPlainText(line)
        #     v1.ensureCursorVisible()

        self.insertPlainText(line)
        self.ensureCursorVisible()

    def flush(self):
        """Stream compatibility, does nothing."""
        pass

    def _set_cursor(self, startline=False, endline=False):
        """
        Set the cursor to the appropriate position, ensuring it is on the last line, after the prompt. If 'startline'
        is true or the cursor is somewhere not after the last prompt, the cursor is placed just after the last prompt.
        If 'endline' is true then the cursor goes at the end of the last line.
        """

        doc = self.document()
        cursor = self.textCursor()
        doclen = len(doc.toPlainText())
        blocklen = len(doc.lastBlock().text())
        promptlen = len(self.currentPrompt)
        startlinepos = doclen - blocklen + promptlen

        if endline:
            cursor.setPosition(doclen)
        elif startline or cursor.position() < startlinepos:
            cursor.setPosition(min(doclen, startlinepos))

        self.setTextCursor(cursor)

    def get_current_line(self):
        """Get the current statement being entered, minus the prompt"""

        promptlen = len(self.currentPrompt)
        return str(self.document().lastBlock().text())[promptlen:]

    def clear_current_line(self):
        """Remove the current statement, leaving only the prompt"""

        self._set_cursor(endline=True)

        for i in self.get_current_line():
            self.textCursor().deletePreviousChar()

    def focusOutEvent(self, event):
        self.is_meta_down = False
        self.metadown = 0
        QtWidgets.QTextEdit.focusOutEvent(self, event)

    def keyReleaseEvent(self, event):
        if event.key() in self.metakeys:
            self.is_meta_down = False
            self.metadown ^= event.key()

        QtWidgets.QTextEdit.keyReleaseEvent(self, event)

    def insertFromMimeData(self, src):
        """Triggered when pasting text, print out then interpret this line-by-line"""
        self.send_input_block(src.text())

    def keyPressEvent(self, event):
        """
        Interpret key presses and move the cursor as necessary. If enter/return is pressed, the current statement is
        sent to be interpreted. Up and down cycle through the statement history. Usually the method of the superclass
        is called but this is omitted when preserving correct cursor position for some keys (eg. backspace).
        """

        key = event.key()
        call_super = key not in (Qt.Key_Up, Qt.Key_Down)

        if key in self.metakeys:
            self.is_meta_down = True
            self.metadown |= key

        if key in (Qt.Key_Return, Qt.Key_Enter):  # execute the current line
            self._set_cursor(endline=True)  # move the cursor to the end so that the new line is done correctly
            self.send_input_line(self.get_current_line())
        elif not self.is_meta_down:
            self._set_cursor()  # ensure cursor is correctly positioned, don't move it if doing meta commands eg. ctrl+c

        if key == Qt.Key_Up:  # previous history item
            if len(self.history) > 0 and self.historypos > -len(self.history):
                if self.historypos == 0:
                    self.curline = self.get_current_line()

                self.historypos -= 1
                self.clear_current_line()
                self.write(self.history[self.historypos])

        if key == Qt.Key_Down:  # next history item
            if len(self.history) > 0 and self.historypos < 0:
                self.historypos += 1
                self.clear_current_line()
                if self.historypos == 0:
                    self.write(self.curline)
                    self.curline = ''
                else:
                    self.write(self.history[self.historypos])

        # prevent backspacing over the prompt
        if key == Qt.Key_Backspace and self.textCursor().positionInBlock() <= len(self.currentPrompt):
            call_super = False

        if call_super:
            QtWidgets.QTextEdit.keyPressEvent(self, event)

        # don't move the cursor if a meta key combination (such as ctrl+c) is pressed
        if not self.is_meta_down and key not in (Qt.Key_Return, Qt.Key_Enter):
            self._set_cursor()

        # restore the prompt if undo has removed it
        if self.is_meta_down and key == Qt.Key_Z and not str(self.document().lastBlock().text()).strip():
            self.write(self.currentPrompt)
            self._set_cursor(endline=True)

        # disallow OS X specific key combo of Cmd+Left or Ctrl+a to go past the prompt
        if is_darwin:
            if ((self.metadown & Qt.Key_Control) and key == Qt.Key_Left) or (
                    (self.metadown & Qt.Key_Meta) and key == Qt.Key_A):
                self._set_cursor()
