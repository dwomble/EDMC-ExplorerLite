"""Look up the galactic region for systems"""

# Copied & modified from https://github.com/klightspeed/EliteDangerousRegionMap/blob/master/RegionMap.py
# Original license:
#
# MIT License
# 
# Copyright (c) 2020 Ben Peddell
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Optional

from data.RegionMapData import regions, regionmap

x0 = -49985
y0 = -40985
z0 = -24105

def find_region(x:float, y:float, z:float) -> Optional[str]:
    """Get the name of the galactic region for the given position."""

    px = int((x - x0) * 83 / 4096)
    pz = int((z - z0) * 83 / 4096)
    
    if px < 0 or pz < 0 or pz >= len(regionmap):
        return None
    else:
        row = regionmap[pz]
        rx = 0
        
        for rl, pv in row:
            if px < rx + rl:
                break
            else:
                rx += rl
        else:
            pv = 0

        if pv == 0:
            return None
        else:
            return regions[pv]
