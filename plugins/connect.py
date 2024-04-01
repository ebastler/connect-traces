# This file is published under MIT License
# Copyright (c) 2024 Pablo Martinez (elpekenin)

from pathlib import Path
from typing import Tuple

import pcbnew as P
import wx

INF = float("inf")  # slope of a vertical line
Point = Tuple[int, int]

THIS = Path(__file__)
ICON = THIS.parent.resolve() / "connect.png"


class ConnectExtensionError(Exception):
    """
    Custom class to flag errors during execution.
    They are handled and cause an error message.

    Other (unexpected) problems will still raise ConnectExtensionError the way.
    """

    def __init__(self, msg: str):
        self.msg = msg


class TrackProxy:
    """Proxy a track, for pythonic names and little convenience."""

    def __init__(self, track: P.PCB_TRACK):
        self._track = track

    @property
    def start(self) -> Point:
        start = self._track.GetStart()
        return start.x, start.y
    
    @start.setter
    def start(self, point: Point):
        return self._track.SetStart(P.VECTOR2I(*point))

    @property
    def end(self) -> Point:
        end = self._track.GetEnd()
        return end.x, end.y
    
    @end.setter
    def end(self, point: Point):
        return self._track.SetEnd(P.VECTOR2I(*point))
    
    @property
    def slope(self) -> float:
        start_x, start_y = self.start
        end_x, end_y = self.end

        delta_x, delta_y = end_x - start_x, end_y - start_y

        if delta_x == 0:
            return INF

        return delta_y / delta_x

    @property
    def layer(self):
        return self._track.GetLayer()


class Horizontal:
    """Represent a line in 2D space."""

    def __init__(self, track: TrackProxy):
        _, self.y = track.start


class Vertical:
    """Represent a line in 2D space."""

    def __init__(self, track: TrackProxy):
        self.x, _ = track.start


class Slanted:
    """Represent a line in 2D space."""

    def __init__(self, track: TrackProxy):
        x, y = track.start
        self.m = track.slope
        self.n = y - self.m * x


def line_factory(track: TrackProxy):
    """Get the correct class."""

    slope = track.slope

    if slope == 0:
        return Horizontal(track)

    if slope == INF:
        return Vertical(track)

    return Slanted(track)


def find_intersection(track_a: TrackProxy, track_b: TrackProxy) -> Point:
    """Find the intersection of two tracks."""

    line_a = line_factory(track_a)
    line_b = line_factory(track_b)

    def _colinear():
        """Repeated logic that makes colinear tracks become one."""
        a_start, a_end, b_start = track_a.start, track_a.end, track_b.start

        if distance(b_start, a_start) < distance(b_start, a_end):
            return a_start
        else:
            return a_end

    # have an exception ready to be raised
    exc = ConnectExtensionError("Lines are parallel and wont connect.")

    if isinstance(line_a, Horizontal) and isinstance(line_b, Horizontal):
        if line_a.y == line_b.y:
            return _colinear()

        raise exc

    elif isinstance(line_a, Horizontal) and isinstance(line_b, Vertical):
        x = line_b.x
        y = line_a.y

    elif isinstance(line_a, Horizontal) and isinstance(line_b, Slanted):
        y = line_a.y
        x = (y - line_b.n) / line_b.m

    elif isinstance(line_a, Vertical) and isinstance(line_b, Horizontal):
        x = line_a.x
        y = line_b.y

    elif isinstance(line_a, Vertical) and isinstance(line_b, Vertical):
        if line_a.x == line_b.x:
            return _colinear()

        raise exc

    elif isinstance(line_a, Vertical) and isinstance(line_b, Slanted):
        x = line_a.x
        y = line_b.m * x + line_b.n

    elif isinstance(line_a, Slanted) and isinstance(line_b, Horizontal):
        y = line_b.y
        x = (y - line_a.n) / line_a.m

    elif isinstance(line_a, Slanted) and isinstance(line_b, Vertical):
        x = line_b.x
        y = line_a.m * x + line_a.n

    elif isinstance(line_a, Slanted) and isinstance(line_b, Slanted):
        m1, n1 = line_a.m, line_a.n
        m2, n2 = line_b.m, line_b.n

        if m1 == m2:
            if n1 == n2:
                return _colinear()

            raise exc

        x = (n2 - n1) / (m1 - m2)
        y = m1 * x + n1

    # all combinations should be checked already
    else:
        raise ConnectExtensionError(f"Unhandled combination: {type(line_a)}, {type(line_b)}")

    # points in KiCAD are ints, cast them
    # done here, at the very end, to avoid carrying rounding errors
    return int(x), int(y)


def distance(a: Point, b: Point):
    """Find the distance between two points."""
    return (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2


def extend_to(track: TrackProxy, point: Point):
    """Extend a line up to the point"""

    dist_start = distance(point, track.start)
    dist_end   = distance(point, track.end)
    if dist_start < dist_end:
        track.start = point
    else:
        track.end = point

class ConnectTraces(P.ActionPlugin):
    """Connect two traces by extending them."""

    def defaults(self):
        """Set default values."""
        self.name = "Connect traces"
        self.category = "Modify PCB"
        self.description = self.__class__.__doc__
        self.show_toolbar_button = True
        self.icon_file_name = str(ICON)

    def _run(self):
        """
        Actual logic, on a function to easily propagate errors by raising,
        instead of returning the error info all the stack thru.
        """

        pcb = P.GetBoard()

        selected_tracks = [TrackProxy(track) for track in pcb.GetTracks() if track.IsSelected()]
        if len(selected_tracks) != 2:
            raise ConnectExtensionError("Wrong amount of tracks, must select 2.")

        a, b = selected_tracks
        if a.layer != b.layer:
            raise ConnectExtensionError("Tracks are on different layers.")

        intersection = find_intersection(a, b)

        extend_to(a, intersection)
        extend_to(b, intersection)

    def Run(self):
        """Execute the logic, converting our expected errors into a text box."""

        try:
            self._run()
        except ConnectExtensionError as e:
            dlg = wx.MessageDialog(None, str(e.msg), "Error", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return 1
