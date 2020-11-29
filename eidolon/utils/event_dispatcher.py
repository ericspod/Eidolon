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

import collections
import threading

__all__ = ["EventDispatcher"]


class EventDispatcher:
    """
    Event broadcast class which invokes callable objects when an EventType event occurs. For every named event, this
    maintains a list of callback callable objects which accept a set of parameters specific for each event type. When
    _triggerEvent() is called, each callback associated with the given event name is called with the given arguments
    passed in. If the callback returns True then subsequent callbacks for that type are ignored. A second list of post
    event handlers is also maintained which is processed after regular events with the return value ignored. This can be
    used to register events which must occur last and which must not be skipped.
    """

    def __init__(self):
        self.handlers = collections.defaultdict(list)
        self.lock = threading.Lock()
        self.suppressed_events = set()

    def trigger_event(self, name, **kwargs):
        """
        Broadcast event to handler callback functions, stopping for any regular callback that returns True. For every
        callback associated with event `name', call it expanding `args' as the arguments. This must be called in the
        main thread. Callbacks stored as post event handlers are called after regular ones with the stop feature ignored.
        """

        def _trigger_handlers(handlers, allow_break):
            """Trigger each handler in `handlers', allowing breaking the loop if `allowBreak'."""
            discards = set()

            try:
                for hfunc in handlers:
                    try:
                        result = hfunc(**kwargs)
                        if allow_break and result is True:  # skip further handlers if returned True
                            break
                    except RuntimeError:
                        discards.add(hfunc)
                        raise
            finally:
                for d in discards:  # throw out all handlers that raised RuntimeError
                    handlers.remove(d)

        with self.lock:
            if name in self.suppressed_events:
                return

            self.suppressed_events.add(name)  # ensure events don't trigger themselves, thus causing an infinite loop

        try:
            _trigger_handlers(self.handlers[name], True)  # regular handlers
        finally:
            with self.lock:
                self.suppressed_events.remove(name)

    def add_handler(self, name, hfunc, is_priority=False):
        """
        Add the callback callable `cb' for event named `name'. If `isPriority', `cb' is placed at the start of the event
        list, and the end otherwise. If `isPostEvent' is True then `cb' is added as a post event callback which is then
        called after regular callbacks with the return value ignored, ie. always gets called.
        """
        events = self.handlers[name]
        events.insert(0 if is_priority else len(events), hfunc)

    def remove_handler(self, hfunc):
        """Remove the callback `cb' from wherever it occurs."""
        for hfuncs in list(self.handlers.values()):
            hfuncs[:] = [h for h in hfuncs if h is not hfunc]
