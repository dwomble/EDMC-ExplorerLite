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
from typing import Any

from .debug import Debug

class Overlay:
    """
    Thin wrapper around `edmcoverlay.Overlay()` (the shared transport for both the classic
    EDMCOverlay plugin and EDMCModernOverlay's compatibility shim) plus EDMCModernOverlay's
    `define_plugin_group` layout API.

    Every method is safe to call regardless of whether an overlay is installed/running --
    check `.available`/`.is_modern` if you need to know, but there's no need to guard calls.
    """

    def __init__(self) -> None:
        self._overlay:Any = None
        self.available:bool = False
        self.is_modern:bool = False
        self._warned:bool = False

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
            Debug.logger.info(f"Overlay detected ({'modern' if self.is_modern else 'legacy'})")
        except Exception as e:
            Debug.logger.warning("Overlay plugin found but failed to initialize", exc_info=e)

    def send_text(self, id:str, text:str, color:str, x:int, y:int, ttl:int = 4, size:str = "normal") -> None:
        """ Send/update a text message. No-op if no overlay is available. """
        if not self.available: return
        try:
            self._overlay.send_message(id, text, color, x, y, ttl=ttl, size=size)
            self._warned = False
        except Exception as e:
            self._fail("send_text", e)

    def send_shape(self, id:str, shape:str, border_color:str, fill_color:str, x:int, y:int, w:int, h:int, ttl:int = 4) -> None:
        """ Send/update a rectangle or other filled shape. No-op if no overlay is available. """
        if not self.available: return
        try:
            self._overlay.send_shape(id, shape, border_color, fill_color, x, y, w, h, ttl=ttl)
            self._warned = False
        except Exception as e:
            self._fail("send_shape", e)

    def send_vect(self, id:str, vector:list[dict], color:str, ttl:int = 4, fill_color:str = "") -> None:
        """ Send/update a vector shape (e.g. a polygon or ring) from a list of {'x':.., 'y':..} points. """
        if not self.available: return
        try:
            self._overlay.send_shape(id, "vect", color, fill_color, 0, 0, 0, 0, vector=vector, ttl=ttl)
            self._warned = False
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

    def _fail(self, op:str, exc:Exception) -> None:
        """ Log the first failure only, then go quiet -- an overlay that vanishes mid-session shouldn't spam the log. """
        if not self._warned:
            self._warned = True
            Debug.logger.warning(f"Overlay {op} failed, disabling further overlay output this session", exc_info=exc)
        self.available = False
