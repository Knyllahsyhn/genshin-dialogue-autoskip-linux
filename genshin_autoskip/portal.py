"""Wayland backend: window capture through xdg-desktop-portal ScreenCast + PipeWire.

On first use the desktop shows a dialog to pick the Genshin window. The portal
returns a restore token, which is stored and passed on later sessions so the
dialog does not appear again (as long as the compositor can match the window).

Frames arrive on a GStreamer streaming thread; only the newest one is kept.
Compositors send frames on damage only, so a static scene keeps its last frame.
"""
from __future__ import annotations

import itertools
import os
import sys
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstVideo", "1.0")
from gi.repository import Gio, GLib, Gst, GstVideo  # noqa: E402

from genshin_autoskip import detector  # noqa: E402
from genshin_autoskip.window import (  # noqa: E402
    PortalCancelled,
    PortalError,
    _PatchReader,
    clamp_patch,
    patch_from_frame,
)

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST = "org.freedesktop.portal.ScreenCast"
REQUEST = "org.freedesktop.portal.Request"
SESSION = "org.freedesktop.portal.Session"
REGISTRY = "org.freedesktop.host.portal.Registry"

# App id under which the skipper registers with the portal. The desktop
# environment looks up the matching .desktop file to name the requesting app
# in the screen sharing dialog. Restore tokens are bound to this id.
APP_ID = "io.github.knyllahsyhn.GenshinAutoskip"
DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=Genshin Auto-Skip
Comment=Dialogue auto-skipper for Genshin Impact (reads the game window)
Exec="{python}" -m genshin_autoskip.main
Icon=input-keyboard
Terminal=true
NoDisplay=true
"""

SOURCE_WINDOW = 2
CURSOR_HIDDEN = 1
PERSIST_UNTIL_REVOKED = 2

DIALOG_TIMEOUT = 120.0
FIRST_FRAME_TIMEOUT = 5.0

# BGRx and BGRA share the byte layout the decoder expects. max-framerate is
# negotiated with the compositor (KWin then copies only 20 frames/s), matching
# the 50 ms period of the main loop.
PIPELINE = (
    "pipewiresrc fd={fd} path={node} do-timestamp=true ! "
    "video/x-raw,max-framerate=20/1 ! "
    "videoconvert ! video/x-raw,format={{BGRx,BGRA}} ! "
    "appsink name=sink emit-signals=true max-buffers=1 drop=true sync=false"
)

_counter = itertools.count()
_registered = False


def desktop_file() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "applications" / f"{APP_ID}.desktop"


def install_desktop_file() -> None:
    """Write the .desktop file the portal dialog takes the app name from."""
    # GLib rejects entries whose Exec program cannot be found, and the venv's
    # bin directory is not on the portal's PATH: use the absolute interpreter.
    entry = DESKTOP_ENTRY.format(python=sys.executable)
    path = desktop_file()
    try:
        if path.exists() and path.read_text() == entry:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(entry)
    except OSError:
        pass


def token_file() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "genshin-autoskip" / "portal-restore-token"


def load_token() -> str | None:
    try:
        return token_file().read_text().strip() or None
    except OSError:
        return None


def save_token(token: str) -> None:
    path = token_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token)
    except OSError:
        pass


class _Portal:
    """Minimal synchronous client for the request/response portal protocol."""

    def __init__(self) -> None:
        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error as err:
            raise PortalError(f"no session bus: {err.message}") from err
        self._sender = self.bus.get_unique_name()[1:].replace(".", "_")
        self._register()

    def _register(self) -> None:
        """Associate this connection with APP_ID (once; must precede other calls).

        Without it the portal sees an anonymous host app and the dialog
        cannot say who asks. Older portals lack the Registry; that is fine.
        """
        global _registered
        if _registered:
            return
        _registered = True
        install_desktop_file()
        try:
            self.call(
                "Register", GLib.Variant("(sa{sv})", (APP_ID, {})), iface=REGISTRY
            )
        except PortalError as err:
            print(f"Warning: portal app registration failed ({err}); "
                  "the sharing dialog will not name this app.", file=sys.stderr)

    def _token(self) -> str:
        return f"genshin_autoskip_{os.getpid()}_{next(_counter)}"

    def request(self, method: str, build_params, timeout: float = DIALOG_TIMEOUT) -> dict:
        """Call a portal method and wait for the Response signal of its request."""
        token = self._token()
        path = f"{PORTAL_PATH}/request/{self._sender}/{token}"
        response: dict = {}

        def on_response(_conn, _sender, _path, _iface, _signal, params):
            code, results = params.unpack()
            response["code"] = code
            response["results"] = results

        # Subscribe before calling so a fast response cannot be missed.
        sub = self.bus.signal_subscribe(
            PORTAL_BUS, REQUEST, "Response", path, None,
            Gio.DBusSignalFlags.NONE, on_response,
        )
        try:
            self.call(method, build_params(token))
            context = GLib.MainContext.default()
            deadline = time.monotonic() + timeout
            while "code" not in response:
                if time.monotonic() > deadline:
                    raise PortalError(f"{method}: no answer from the portal")
                if not context.iteration(False):
                    time.sleep(0.02)
        finally:
            self.bus.signal_unsubscribe(sub)

        if response["code"] == 1:
            raise PortalCancelled(f"{method}: cancelled in the portal dialog")
        if response["code"] != 0:
            raise PortalError(f"{method}: portal returned code {response['code']}")
        return response["results"]

    def call(self, method: str, params: GLib.Variant, iface: str = SCREENCAST,
             path: str = PORTAL_PATH):
        try:
            return self.bus.call_sync(
                PORTAL_BUS, path, iface, method, params, None,
                Gio.DBusCallFlags.NONE, -1, None,
            )
        except GLib.Error as err:
            raise PortalError(f"{method}: {err.message}") from err

    def open_pipewire_remote(self, session: str) -> int:
        try:
            result, fds = self.bus.call_with_unix_fd_list_sync(
                PORTAL_BUS, PORTAL_PATH, SCREENCAST, "OpenPipeWireRemote",
                GLib.Variant("(oa{sv})", (session, {})), GLib.VariantType("(h)"),
                Gio.DBusCallFlags.NONE, -1, None, None,
            )
        except GLib.Error as err:
            raise PortalError(f"OpenPipeWireRemote: {err.message}") from err
        return fds.get(result.unpack()[0])

    def close_session(self, session: str) -> None:
        try:
            self.call("Close", None, iface=SESSION, path=session)
        except PortalError as err:
            print(f"Warning: portal app registration failed ({err}); "
                  "the sharing dialog will not name this app.", file=sys.stderr)


def start_screencast(portal: _Portal) -> tuple[str, int]:
    """Run the portal handshake; return (session handle, PipeWire node id)."""
    results = portal.request(
        "CreateSession",
        lambda token: GLib.Variant("(a{sv})", ({
            "handle_token": GLib.Variant("s", token),
            "session_handle_token": GLib.Variant("s", token),
        },)),
    )
    session = results["session_handle"]
    try:
        options = {
            "types": GLib.Variant("u", SOURCE_WINDOW),
            "multiple": GLib.Variant("b", False),
            "cursor_mode": GLib.Variant("u", CURSOR_HIDDEN),
            "persist_mode": GLib.Variant("u", PERSIST_UNTIL_REVOKED),
        }
        restore = load_token()
        if restore:
            options["restore_token"] = GLib.Variant("s", restore)
        portal.request(
            "SelectSources",
            lambda token: GLib.Variant(
                "(oa{sv})", (session, {**options, "handle_token": GLib.Variant("s", token)})
            ),
        )
        results = portal.request(
            "Start",
            lambda token: GLib.Variant(
                "(osa{sv})", (session, "", {"handle_token": GLib.Variant("s", token)})
            ),
        )
        if results.get("restore_token"):
            save_token(results["restore_token"])
        streams = results.get("streams") or []
        if not streams:
            raise PortalError("Start: portal returned no stream")
        return session, streams[0][0]
    except BaseException:
        portal.close_session(session)
        raise


class PortalWindow(_PatchReader):
    """Genshin window as a PipeWire stream; same interface as GenshinWindow."""

    def __init__(self, portal: _Portal, session: str, fd: int, node: int) -> None:
        self._portal = portal
        self._session = session
        self._fd = fd
        self._lock = threading.Lock()
        self._frame: tuple[Gst.Buffer, int, int, int] | None = None
        self._caps: Gst.Caps | None = None
        self._layout: tuple[int, int, int] | None = None
        self._failed = False
        self.frames = 0

        self._pipeline = Gst.parse_launch(PIPELINE.format(fd=fd, node=node))
        sink = self._pipeline.get_by_name("sink")
        sink.connect("new-sample", self._on_sample)
        self._bus = self._pipeline.get_bus()
        if self._pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.close()
            raise PortalError("could not start the PipeWire pipeline")

    @classmethod
    def open(cls) -> "PortalWindow":
        Gst.init(None)
        portal = _Portal()
        session, node = start_screencast(portal)
        try:
            fd = portal.open_pipewire_remote(session)
        except BaseException:
            portal.close_session(session)
            raise
        win = cls(portal, session, fd, node)
        if not win.wait_for_frame(FIRST_FRAME_TIMEOUT):
            win.close()
            raise PortalError("no frame from the PipeWire stream")
        return win

    def _on_sample(self, sink) -> Gst.FlowReturn:
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.OK
        caps = sample.get_caps()
        if caps is not self._caps:
            info = GstVideo.VideoInfo.new_from_caps(caps)
            self._caps = caps
            self._layout = (info.width, info.height, info.stride[0])
        with self._lock:
            self._frame = (sample.get_buffer(), *self._layout)
            self.frames += 1
        return Gst.FlowReturn.OK

    def wait_for_frame(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._current() is not None:
                return True
            time.sleep(0.05)
        return False

    def _current(self):
        if self._failed:
            return None
        msg = self._bus.pop_filtered(Gst.MessageType.ERROR | Gst.MessageType.EOS)
        if msg is not None:
            # stream ended: window closed, capture revoked or compositor gone
            self._failed = True
            return None
        with self._lock:
            return self._frame

    def size(self) -> tuple[int, int] | None:
        frame = self._current()
        return None if frame is None else (frame[1], frame[2])

    def read_pixel(self, x: int, y: int) -> detector.Pixel | None:
        patch = self.read_patch(x, y, 0)
        return None if not patch else patch[0]

    def read_patch(
        self, cx: int, cy: int, radius: int, size: tuple[int, int] | None = None
    ) -> list[detector.Pixel] | None:
        frame = self._current()
        if frame is None:
            return None
        buffer, width, height, stride = frame
        rect = clamp_patch(cx, cy, radius, (width, height))
        if rect is None:
            return None
        x0, y0, w, h = rect
        # Copy only the rows the patch touches, not the whole frame.
        start = y0 * stride
        rows = buffer.extract_dup(start, h * stride)
        return patch_from_frame(rows, stride, x0, 0, w, h)

    def screenshot(self):
        from PIL import Image

        frame = self._current()
        if frame is None:
            return None
        buffer, width, height, stride = frame
        data = buffer.extract_dup(0, height * stride)
        return Image.frombytes("RGB", (width, height), data, "raw", "BGRX", stride)

    def close(self) -> None:
        try:
            self._pipeline.set_state(Gst.State.NULL)
        except Exception:
            pass
        self._portal.close_session(self._session)
        try:
            os.close(self._fd)
        except OSError:
            pass
