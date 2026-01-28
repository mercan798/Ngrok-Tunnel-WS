
import asyncio
import websockets

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Input, Button, RichLog


ONE_SOCIETY_BIG = r"""
  ___   _   _  ___     ___   ___   ___ ___ ___ _____ _   _
 / _ \ | \ | || __|   / __| / _ \ / __|_ _| __|_   _| | | |
| (_) ||  \| || _|    \__ \| (_) | (__ | || _|  | | | |_| |
 \___/ |_| \_||___|   |___/ \___/ \___|___|___| |_|  \___/
"""


class Comp(App):
    CSS_PATH="style.css"

    ws=None


def to_ws_base(server: str) -> str:

    server = (server or "").strip().rstrip("/")
    if server.startswith("https://"):
        return "wss://" + server[len("https://"):]
    if server.startswith("http://"):
        return "ws://" + server[len("http://"):]
    if server.startswith("ws://") or server.startswith("wss://"):
        return server
    return "ws://" + server


class OneSocietyTUI(App):
    ws = None
    connected = False

    server = ""
    room = ""
    user = ""
    key = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="frame"):
            yield Static(
                Align.center(
                    Panel(
                        ONE_SOCIETY_BIG,
                        border_style="red",
                        padding=(0, 1)
                    )
                ),
                id="brand"
            )

            yield Static("ENTER ACCESS CREDENTIALS", id="status")

            with Vertical(id="login_panel"):
                yield Input(placeholder="Server (https://xxxx.ngrok-free.dev)", id="server")
                yield Input(placeholder="Room (e.g. one)", id="room")
                yield Input(placeholder="Username / Callsign", id="user")
                yield Input(placeholder="Password", password=True, id="key")

                with Horizontal():
                    yield Button("ENTER", id="enter")
                    yield Button("QUIT", id="quit")


            with Horizontal(id="main_grid"):
                with Vertical(id="left_panel"):
                    yield Static("[b]ACCESS HUD[/b]\nSecure Channel • 2 Nodes Max", id="left_title")
                    yield Static("", id="left_info")
                    yield Static(
                        "SYS Booting modules…\n- WS tunnel: pending\n- Node limit: 2\n- Status: OFFLINE",
                        id="hud",
                    )

                with Vertical(id="right_panel"):
                    yield Static("CHANNEL: /ws    STATUS: OFFLINE", id="feed_hdr")
                    yield RichLog(id="chatlog", wrap=True, markup=False)
                    with Horizontal(id="send_row"):
                        yield Input(placeholder="Type message… (Enter)   /leave", id="msg")
                        yield Button("SEND", id="send")

        yield Footer()

    async def on_mount(self) -> None:

        self.query_one("#main_grid").display = False


    def set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    def set_online(self, on: bool) -> None:
        hud = self.query_one("#hud", Static)
        feed = self.query_one("#feed_hdr", Static)

        if on:
            hud.update("SYS Modules ready.\n- WS tunnel: OK\n- Node limit: 2\n- Status: ONLINE")
            feed.update("CHANNEL: /ws    STATUS: ONLINE")
        else:
            hud.update("SYS Booting modules…\n- WS tunnel: DOWN\n- Node limit: 2\n- Status: OFFLINE")
            feed.update("CHANNEL: /ws    STATUS: OFFLINE")

    def chat_write(self, renderable) -> None:
        self.query_one("#chatlog", RichLog).write(renderable)

    def bubble(self, sender: str, text: str, kind: str):
            if kind == "sys":
                panel = Panel(
                    Text(text, style="bold"),
                    border_style="red",
                    padding=(0, 1),
                )
                return Align.center(panel)

            border = "red" if kind == "me" else "white"
            panel = Panel(Text(text), title=sender, border_style=border, padding=(0, 1))
            return Align.right(panel) if kind == "me" else Align.left(panel)




    async def loading_sequence(self) -> None:

        steps = [
            "WELCOME ONE SOCIETY — LOADING…",
            "SYNCING MODULES…",
            "OPENING SECURE SOCKET…",
        ]
        for s in steps:
            self.set_status(s)
            await asyncio.sleep(2)
        self.set_status("Welcome")

    # ---------- ws ----------
    async def connect_ws(self) -> None:
        ws_base = to_ws_base(self.server)
        ws_url = f"{ws_base}/ws?room={self.room}&key={self.key}&user={self.user}"

        try:
            self.ws = await websockets.connect(ws_url, ping_interval=20, ping_timeout=20)
        except Exception as e:
            self.connected = False
            self.set_online(False)
            self.query_one("#main_grid").display = False
            self.query_one("#login_panel").display = True
            self.set_status(f"CONNECT FAILED: {e}")
            return

        self.connected = True
        self.set_online(True)


        self.query_one("#login_panel").display = False
        self.query_one("#main_grid").display = True

        self.query_one("#left_info", Static).update(
            f"[b]CALLSIGN[/b]: {self.user}\n[b]ROOM[/b]: {self.room}\n[b]SERVER[/b]: {self.server}"
        )

        self.chat_write(self.bubble("SYS", "connected. /leave to exit", "sys"))
        asyncio.create_task(self.receiver())

    async def receiver(self) -> None:
        try:
            async for msg in self.ws:
                # SYS
                if msg.startswith("[SYS]"):
                    self.chat_write(self.bubble("SYS", msg, "sys"))
                    continue

                # Normal: "[name] message"
                if msg.startswith("[") and "]" in msg:
                    sender = msg[1:msg.index("]")]
                    text = msg[msg.index("]") + 1 :].lstrip()
                    kind = "me" if sender == self.user else "other"
                    self.chat_write(self.bubble(sender, text, kind))
                else:
                    self.chat_write(self.bubble("unknown", msg, "other"))
        except Exception:
            self.chat_write(self.bubble("SYS", "disconnected", "sys"))
        finally:
            self.connected = False
            self.set_online(False)


    async def send_msg(self) -> None:
        if not self.connected or not self.ws:
            self.chat_write(self.bubble("SYS", "not connected", "sys"))
            return

        msg_input = self.query_one("#msg", Input)
        text = msg_input.value.strip()
        if not text:
            return
        msg_input.value = ""

        if text == "/leave":
            try:
                await self.ws.close()
            except Exception:
                pass
            self.exit()
            return

        try:
            await self.ws.send(text)
            self.chat_write(self.bubble(self.user, text, "me"))
        except Exception as e:
            self.chat_write(self.bubble("SYS", f"send failed: {e}", "sys"))


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.exit()

        if event.button.id == "enter":
            self.server = self.query_one("#server", Input).value.strip()
            self.room = self.query_one("#room", Input).value.strip() or "one"
            self.user = self.query_one("#user", Input).value.strip() or "unknown"
            self.key = self.query_one("#key", Input).value.strip()

            if not self.server or not self.key:
                self.set_status("SERVER + PASSWORD REQUIRED")
                return

            await self.loading_sequence()
            await self.connect_ws()

        if event.button.id == "send":
            await self.send_msg()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "msg":
            await self.send_msg()


if __name__ == "__main__":
    OneSocietyTUI().run()
