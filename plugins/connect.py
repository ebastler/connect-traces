# This file is published under MIT License
# Copyright (c) 2024 Pablo Martínez (elpekenin)

import os
from typing import Tuple

import pcbnew as P

Point = Tuple[int, int]


class TrackProxy:
    """Proxy a track, for easier coord manipulation."""

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

        return delta_y / delta_x


def line_props(track: TrackProxy):
    """Get the `y = mx+n` representation of a track."""

    x, y = track.start

    m = track.slope
    n = y - track.slope * x

    return m, n


def find_intersection(a: TrackProxy, b: TrackProxy) -> Point:
    """Find the intersection of two tracks."""

    m1, n1 = line_props(a)
    m2, n2 = line_props(b)

    if m1 == m2:
        raise ValueError("Lines are parallel and wont connect")

    x = (n2 - n1) / (m1 - m2)
    y = m1 * x + n1

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
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "./connect.png")

    def Run(self):
        pcb = P.GetBoard()

        selected_tracks = [TrackProxy(track) for track in pcb.GetTracks() if track.IsSelected()]
        if len(selected_tracks) != 2:
            raise ValueError("Wrong amount of tracks, must select 2.")

        # actual logic, extend them to their intersection point
        a, b = selected_tracks
        intersection = find_intersection(a, b)
        extend_to(a, intersection)
        extend_to(b, intersection)
