"""
Generic wrapper around the EDMC overlay ecosystem.

Handles detection of whichever overlay backend is installed -- the classic `EDMCOverlay`
plugin, or EDMCModernOverlay (which ships an `edmcoverlay`-compatible shim for the same
message/shape transport, plus its own `overlay_plugin.overlay_api.define_plugin_group` for
layout/grouping/backgrounds) -- and exposes a small set of primitives that no-op cleanly
when no overlay is installed or running.

This stays deliberately low-level: no per-frame config table, no plugin-specific frame
names/colors/positions. A consuming plugin builds that ergonomic layer on top, supplying its
own frame names and layout on every call.
"""
import inspect
from typing import Any

from .debug import Debug

class Overlay:
    """
    Thin wrapper around `edmcoverlay.Overlay()` (the shared transport for both the classic
    EDMCOverlay plugin and EDMCModernOverlay's compatibility shim) plus EDMCModernOverlay's
    `define_plugin_group` layout API.

    Every method is safe to call regardless of whether an overlay is installed/running --
    check `.available`/`.is_modern`/`.supports_circle` if you need to know, but there's no
    need to guard calls.
    """

    FAILURE_THRESHOLD:int = 5 # consecutive failures before giving up on this overlay for the rest of the session

    def __init__(self) -> None:
        self._overlay:Any = None
        self.available:bool = False
        self.is_modern:bool = False
        self.supports_circle:bool = False # a native "circle" send_shape -- pre-release as of this writing
        self._warned:bool = False
        self._consecutive_failures:int = 0

        self._detect()

    def _detect(self) -> None:
        """ Probe for an installed overlay backend, same pattern as EDMC-PluginLib's load.py:get_overlay(). """
        try:
            from EDMCOverlay import edmcoverlay # type: ignore
        except ImportError:
            try:
                from edmcoverlay import edmcoverlay # type: ignore
            except ImportError:
                Debug.logger.info("No overlay plugin detected")
                return

        try:
            from overlay_plugin.overlay_api import define_plugin_group # type: ignore
            self.is_modern = True
        except ImportError:
            self.is_modern = False

        try:
            self._overlay = edmcoverlay.Overlay()
            self.available = True
            self.supports_circle = self._detect_circle_support()
            Debug.logger.info(f"Overlay detected ({'modern' if self.is_modern else 'legacy'})")
        except Exception as e:
            Debug.logger.warning("Overlay plugin found but failed to initialize", exc_info=e)

    def _detect_circle_support(self) -> bool:
        """ Same process, real imported class -- introspect send_shape's actual signature for
        the pre-release circle kwargs (radius/thickness) rather than guessing from a version
        string EDMCModernOverlay doesn't expose to callers anyway. """
        try:
            return "radius" in inspect.signature(self._overlay.send_shape).parameters
        except Exception:
            return False

    def send_text(self, id:str, text:str, color:str, x:int, y:int, ttl:int = 4, size:str = "normal") -> None:
        """ Send/update a text message. No-op if no overlay is available. """
        if not self.available: return
        try:
            self._overlay.send_message(id, text, color, x, y, ttl=ttl, size=size)
            self._succeed()
        except Exception as e:
            self._fail("send_text", e)

    def send_shape(self, id:str, shape:str, border_color:str, fill_color:str, x:int, y:int, w:int, h:int, ttl:int = 4) -> None:
        """ Send/update a rectangle or other filled shape. No-op if no overlay is available. """
        if not self.available: return
        try:
            self._overlay.send_shape(id, shape, border_color, fill_color, x, y, w, h, ttl=ttl)
            self._succeed()
        except Exception as e:
            self._fail("send_shape", e)

    def send_circle(self, id:str, border_color:str, fill_color:str, x:int, y:int, radius:int, thickness:int, ttl:int = 4) -> None:
        """ A native filled/outlined circle -- check `.supports_circle` before calling; a
        backend without this (pre-release) support just drops a shape="circle" payload. """
        if not self.available: return
        try:
            self._overlay.send_shape(
                id, "circle", color=border_color, fill=fill_color, x=x, y=y, radius=radius, thickness=thickness, ttl=ttl,
            )
            self._succeed()
        except Exception as e:
            self._fail("send_circle", e)

    def send_vect(self, id:str, vector:list[dict], color:str, ttl:int = 4, fill_color:str = "") -> None:
        """ Send/update a vector shape (e.g. a polygon or ring) from a list of {'x':.., 'y':..}
        points. Goes through send_raw(), not send_shape() -- confirmed against both backends'
        real source (inorton/EDMCOverlay and EDMCModernOverlay's compat shim): send_shape()'s
        signature is id/shape/color/fill/x/y/w/h/ttl on both, with no `vector` parameter at
        all; a vect payload's points only ever go in via the raw message dict's "vector" key. """
        if not self.available: return
        try:
            self._overlay.send_raw({
                "id": id, "shape": "vect", "color": color, "fill": fill_color,
                "x": 0, "y": 0, "w": 0, "h": 0, "ttl": ttl, "vector": vector,
            })
            self._succeed()
        except Exception as e:
            self._fail("send_vect", e)

    def clear(self, id:str) -> None:
        """ Clear a previously sent message/shape by id, if the backend supports it. """
        if not self.available: return
        try:
            self._overlay.send_message(id, "", "#000000", 0, 0, ttl=1)
        except Exception as e:
            self._fail("clear", e)

    def define_group(self, **kwargs) -> bool:
        """
        Register a plugin group with EDMCModernOverlay for layout/grouping/backgrounds
        (see `overlay_plugin.overlay_api.define_plugin_group` for the accepted kwargs).

        Returns False if unavailable, or if the call fails -- callers should treat that as
        "fall back to unrouted messages", not an error. A failed call also permanently
        disables further define_group() attempts for this instance (older EDMCModernOverlay
        versions may not support every kwarg).
        """
        if not self.is_modern:
            return False
        try:
            from overlay_plugin.overlay_api import define_plugin_group # type: ignore
            define_plugin_group(**kwargs)
            return True
        except Exception as e:
            Debug.logger.debug("EDMCModernOverlay define_plugin_group failed", exc_info=e)
            self.is_modern = False
            return False

    def _succeed(self) -> None:
        self._warned = False
        self._consecutive_failures = 0

    def _fail(self, op:str, exc:Exception) -> None:
        """ A single failure doesn't disable the overlay -- e.g. a one-off bad API call during
        setup (like a define_group() mismatch) shouldn't blackout the rest of the session. Only
        FAILURE_THRESHOLD consecutive failures does, and even then logs just once, so a
        genuinely vanished overlay app goes quiet instead of spamming retries/warnings. """
        self._consecutive_failures += 1
        if self._consecutive_failures < self.FAILURE_THRESHOLD:
            return
        if not self._warned:
            self._warned = True
            Debug.logger.warning(
                f"Overlay {op} failed {self._consecutive_failures} times in a row, disabling further overlay output this session",
                exc_info=exc,
            )
        self.available = False
