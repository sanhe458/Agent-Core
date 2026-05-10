import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Dict, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)

try:
    import aiohttp
    from aiohttp import ClientSession, ClientTimeout, WSMsgType
    AIOHTTP_AVAILABLE = True
except ImportError:
    ClientSession = None
    ClientTimeout = None
    WSMsgType = None
    AIOHTTP_AVAILABLE = False

class NapCatServerConfig:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 3000,
        token: str = "",
        reconnect_delay: float = 5.0,
        heartbeat_interval: float = 30.0,
        action_timeout: float = 30.0
    ):
        self.host = host
        self.port = port
        self.token = token
        self.reconnect_delay = reconnect_delay
        self.heartbeat_interval = heartbeat_interval
        self.action_timeout = action_timeout

    def build_ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}"

class NapCatTransportClient:
    def __init__(
        self,
        logger_instance: logging.Logger = None,
        on_connection_opened: Callable[[], Coroutine[Any, Any, None]] = None,
        on_connection_closed: Callable[[], Coroutine[Any, Any, None]] = None,
        on_payload: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]] = None,
    ):
        self._logger = logger_instance or logger
        self._on_connection_opened = on_connection_opened
        self._on_connection_closed = on_connection_closed
        self._on_payload = on_payload
        self._server_config: Optional[NapCatServerConfig] = None
        self._connection_task: Optional[asyncio.Task[None]] = None
        self._pending_actions: Dict[str, asyncio.Future[Dict[str, Any]]] = {}
        self._background_tasks: Set[asyncio.Task[Any]] = set()
        self._send_lock = asyncio.Lock()
        self._ws: Optional[Any] = None
        self._stop_requested: bool = False
        self._connection_active: bool = False
        self._warned_missing_token: bool = False

    @classmethod
    def is_available(cls) -> bool:
        return AIOHTTP_AVAILABLE

    def configure(self, server_config: NapCatServerConfig) -> None:
        self._server_config = server_config
        self._warned_missing_token = False

    async def start(self) -> None:
        if not self.is_available():
            raise RuntimeError("aiohttp not available, please install aiohttp>=3.9.0")
        if self._server_config is None:
            raise RuntimeError("Server config not set, call configure() first")
        if self._connection_task is not None and not self._connection_task.done():
            return
        self._stop_requested = False
        self._connection_task = asyncio.create_task(self._connection_loop(), name="napcat.connection")

    async def stop(self) -> None:
        self._stop_requested = True
        connection_task = self._connection_task
        self._connection_task = None
        ws = self._ws
        if ws is not None and not ws.closed:
            try:
                await ws.close()
            except Exception:
                pass
        self._ws = None
        if connection_task is not None:
            connection_task.cancel()
            try:
                await connection_task
            except asyncio.CancelledError:
                pass
        await self._cancel_background_tasks()
        await self._notify_connection_closed()
        self._fail_pending_actions("NapCat connection closed")

    async def call_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ws = self._ws
        server_config = self._server_config
        if ws is None or ws.closed or server_config is None:
            raise RuntimeError("NapCat is not connected")
        echo_id = uuid4().hex
        loop = asyncio.get_running_loop()
        response_future: asyncio.Future[Dict[str, Any]] = loop.create_future()
        self._pending_actions[echo_id] = response_future
        request_payload = {"action": action_name, "params": params, "echo": echo_id}
        try:
            async with self._send_lock:
                await ws.send_str(json.dumps(request_payload, ensure_ascii=False))
            return await asyncio.wait_for(response_future, timeout=server_config.action_timeout)
        except asyncio.TimeoutError:
            self._logger.warning(f"NapCat action {action_name} timeout after {server_config.action_timeout}s")
            raise
        finally:
            self._pending_actions.pop(echo_id, None)

    async def _connection_loop(self) -> None:
        while not self._stop_requested:
            server_config = self._server_config
            if server_config is None:
                return
            ws_url = server_config.build_ws_url()
            timeout = ClientTimeout(total=None, connect=10)
            self._log_connection_attempt(ws_url, server_config)
            try:
                async with ClientSession(headers=self._build_headers(server_config), timeout=timeout) as session:
                    async with session.ws_connect(ws_url, heartbeat=server_config.heartbeat_interval) as ws:
                        self._ws = ws
                        self._logger.info(f"NapCat connected: {ws_url}")
                        disconnect_reason = await self._receive_loop(ws)
                        self._log_connection_closed(ws_url, server_config, disconnect_reason)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.warning(f"NapCat connection failed: {exc}{self._build_reconnect_hint(server_config)}")
            finally:
                self._ws = None
                await self._notify_connection_closed()
                self._fail_pending_actions("NapCat connection interrupted")
            if self._stop_requested:
                break
            await asyncio.sleep(server_config.reconnect_delay)

    async def _receive_loop(self, ws: Any) -> str:
        disconnect_reason = "Connection ended"
        bootstrap_task = self._create_background_task(
            self._notify_connection_opened(),
            "napcat.bootstrap",
        )
        try:
            async for ws_message in ws:
                if ws_message.type != WSMsgType.TEXT:
                    if ws_message.type == WSMsgType.CLOSE:
                        disconnect_reason = "Server sent CLOSE frame"
                        break
                    if ws_message.type == WSMsgType.CLOSED:
                        disconnect_reason = "WebSocket closed"
                        break
                    if ws_message.type == WSMsgType.ERROR:
                        disconnect_reason = "WebSocket error"
                        break
                    continue
                payload = self._parse_json_message(ws_message.data)
                if payload is None:
                    continue
                echo_id = str(payload.get("echo") or "").strip()
                if echo_id:
                    self._resolve_pending_action(echo_id, payload)
                    continue
                self._create_background_task(self._on_payload(payload), "napcat.payload")
        finally:
            if bootstrap_task is not None and not bootstrap_task.done():
                bootstrap_task.cancel()
                try:
                    await bootstrap_task
                except asyncio.CancelledError:
                    pass
        return disconnect_reason

    def _create_background_task(self, coroutine: Coroutine, name: str) -> asyncio.Task:
        task = asyncio.create_task(coroutine, name=name)
        self._background_tasks.add(task)
        task.add_done_callback(self._handle_background_task_completion)
        return task

    def _handle_background_task_completion(self, task: asyncio.Task) -> None:
        self._background_tasks.discard(task)
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            self._logger.error(f"NapCat background task error: {exception}", exc_info=True)

    async def _cancel_background_tasks(self) -> None:
        background_tasks = list(self._background_tasks)
        for task in background_tasks:
            task.cancel()
        if background_tasks:
            try:
                await asyncio.gather(*background_tasks, return_exceptions=True)
            except Exception:
                pass
        self._background_tasks.clear()

    async def _notify_connection_opened(self) -> None:
        if self._connection_active:
            return
        self._connection_active = True
        if self._on_connection_opened:
            try:
                await self._on_connection_opened()
            except Exception as exc:
                self._logger.warning(f"Connection opened callback failed: {exc}")

    async def _notify_connection_closed(self) -> None:
        if not self._connection_active:
            return
        self._connection_active = False
        if self._on_connection_closed:
            try:
                await self._on_connection_closed()
            except Exception as exc:
                self._logger.warning(f"Connection closed callback failed: {exc}")

    def _resolve_pending_action(self, echo_id: str, payload: Dict[str, Any]) -> None:
        response_future = self._pending_actions.get(echo_id)
        if response_future is None or response_future.done():
            return
        response_future.set_result(payload)

    def _fail_pending_actions(self, error_message: str) -> None:
        for response_future in self._pending_actions.values():
            if not response_future.done():
                response_future.set_exception(RuntimeError(error_message))
        self._pending_actions.clear()

    def _build_headers(self, server_config: NapCatServerConfig) -> Dict[str, str]:
        if server_config.token:
            return {"Authorization": f"Bearer {server_config.token}"}
        return {}

    def _log_connection_attempt(self, ws_url: str, server_config: NapCatServerConfig) -> None:
        auth_mode = "token configured" if server_config.token else "no token"
        self._logger.debug(f"NapCat connecting: {ws_url} (auth: {auth_mode})")
        if not server_config.token and not self._warned_missing_token:
            self._logger.warning(
                "NapCat no token configured; "
                "if NapCat requires auth, connection may be rejected"
            )
            self._warned_missing_token = True

    def _log_connection_closed(self, ws_url: str, server_config: NapCatServerConfig, reason: str) -> None:
        self._logger.warning(
            f"NapCat disconnected: {ws_url}, {reason}{self._build_reconnect_hint(server_config)}"
        )

    def _build_reconnect_hint(self, server_config: NapCatServerConfig) -> str:
        if self._stop_requested:
            return ""
        return f"; reconnecting in {server_config.reconnect_delay}s"

    def _parse_json_message(self, data: Any) -> Optional[Dict[str, Any]]:
        try:
            payload = json.loads(str(data))
            return payload if isinstance(payload, dict) else None
        except Exception as exc:
            self._logger.warning(f"JSON parse failed: {exc}")
            return None
