import logging
from typing import Any, Dict, List, Optional
from .transport import NapCatTransportClient

logger = logging.getLogger(__name__)

class ActionResult:
    def __init__(self, success: bool, result: Any = None, error: str = None):
        self.success = success
        self.result = result
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        if self.success:
            return {"success": True, "result": self.result}
        return {"success": False, "error": self.error}

class NapCatActionService:
    def __init__(self, transport: NapCatTransportClient, logger_instance: logging.Logger = None):
        self._transport = transport
        self._logger = logger_instance or logger

    async def _call(self, action: str, params: Dict[str, Any] = None) -> ActionResult:
        try:
            response = await self._transport.call_action(action, params or {})
            status = str(response.get("status", "")).lower()
            if status == "ok":
                return ActionResult(True, response.get("data"))
            return ActionResult(False, None, response.get("wording") or response.get("message") or f"Action {action} failed")
        except Exception as e:
            self._logger.error(f"Action {action} error: {e}")
            return ActionResult(False, error=str(e))

    async def _call_no_params(self, action: str) -> ActionResult:
        return await self._call(action)

    async def get_login_info(self) -> ActionResult:
        return await self._call_no_params("get_login_info")

    async def get_version_info(self) -> ActionResult:
        return await self._call_no_params("get_version_info")

    async def get_status(self) -> ActionResult:
        return await self._call_no_params("get_status")

    async def set_qq_profile(self, nickname: str = None, company: str = None, email: str = None, college: str = None, personal_note: str = None) -> ActionResult:
        params = {k: v for k, v in [("nickname", nickname), ("company", company), ("email", email), ("college", college), ("personal_note", personal_note)] if v}
        return await self._call("set_qq_profile", params)

    async def set_self_status(self, status: int, text: str = None) -> ActionResult:
        params = {"status": status}
        if text:
            params["text"] = text
        return await self._call("set_self_status", params)

    async def clean_cache(self) -> ActionResult:
        return await self._call_no_params("clean_cache")

    async def get_stranger_info(self, user_id: int, no_cache: bool = False) -> ActionResult:
        return await self._call("get_stranger_info", {"user_id": user_id, "no_cache": no_cache})

    async def get_friend_list(self) -> ActionResult:
        return await self._call_no_params("get_friend_list")

    async def get_friend_info(self, user_id: int, no_cache: bool = False) -> ActionResult:
        return await self._call("get_friend_info", {"user_id": user_id, "no_cache": no_cache})

    async def get_group_list(self, no_cache: bool = False) -> ActionResult:
        return await self._call("get_group_list", {"no_cache": no_cache})

    async def get_group_info(self, group_id: int, no_cache: bool = False) -> ActionResult:
        return await self._call("get_group_info", {"group_id": group_id, "no_cache": no_cache})

    async def get_group_member_list(self, group_id: int, no_cache: bool = False) -> ActionResult:
        return await self._call("get_group_member_list", {"group_id": group_id, "no_cache": no_cache})

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = False) -> ActionResult:
        return await self._call("get_group_member_info", {"group_id": group_id, "user_id": user_id, "no_cache": no_cache})

    async def get_group_honor_info(self, group_id: int, type: str = "all") -> ActionResult:
        return await self._call("get_group_honor_info", {"group_id": group_id, "type": type})

    async def send_msg(self, message_type: str, content: str, user_id: int = None, group_id: int = None, auto_escape: bool = False) -> ActionResult:
        params = {"message_type": message_type, "message": content, "auto_escape": auto_escape}
        if user_id:
            params["user_id"] = user_id
        if group_id:
            params["group_id"] = group_id
        return await self._call("send_msg", params)

    async def send_private_msg(self, user_id: int, message: str, group_id: int = None, auto_escape: bool = False) -> ActionResult:
        params = {"user_id": user_id, "message": message, "auto_escape": auto_escape}
        if group_id:
            params["group_id"] = group_id
        return await self._call("send_private_msg", params)

    async def send_group_msg(self, group_id: int, message: str, auto_escape: bool = False) -> ActionResult:
        return await self._call("send_group_msg", {"group_id": group_id, "message": message, "auto_escape": auto_escape})

    async def send_msg_ex(self, user_id: int = None, group_id: int = None, message: str = None, auto_escape: bool = False) -> ActionResult:
        params = {"auto_escape": auto_escape}
        if user_id:
            params["user_id"] = user_id
            params["message_type"] = "private"
        if group_id:
            params["group_id"] = group_id
            params["message_type"] = "group"
        if message:
            params["message"] = message
        return await self._call("send_msg", params)

    async def delete_msg(self, message_id: int) -> ActionResult:
        return await self._call("delete_msg", {"message_id": message_id})

    async def get_msg(self, message_id: int) -> ActionResult:
        return await self._call("get_msg", {"message_id": message_id})

    async def get_forward_msg(self, id: str) -> ActionResult:
        return await self._call("get_forward_msg", {"id": id})

    async def send_group_forward_msg(self, group_id: int, messages: List[Dict[str, Any]]) -> ActionResult:
        return await self._call("send_group_forward_msg", {"group_id": group_id, "messages": messages})

    async def send_group_forward_msg_ex(self, group_id: int, message: str) -> ActionResult:
        return await self._call("send_group_forward_msg", {
            "group_id": group_id,
            "messages": [{"type": "node", "data": {"name": "转发", "uin": "10000", "content": message}}]
        })

    async def get_image(self, file: str) -> ActionResult:
        return await self._call("get_image", {"file": file})

    async def can_send_image(self) -> ActionResult:
        return await self._call_no_params("can_send_image")

    async def can_send_record(self) -> ActionResult:
        return await self._call_no_params("can_send_record")

    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> ActionResult:
        return await self._call("set_group_kick", {"group_id": group_id, "user_id": user_id, "reject_add_request": reject_add_request})

    async def set_group_ban(self, group_id: int, user_id: int, duration: int = 1800) -> ActionResult:
        return await self._call("set_group_ban", {"group_id": group_id, "user_id": user_id, "duration": duration})

    async def set_group_whole_ban(self, group_id: int, enable: bool = True) -> ActionResult:
        return await self._call("set_group_whole_ban", {"group_id": group_id, "enable": enable})

    async def set_group_admin(self, group_id: int, user_id: int, enable: bool = True) -> ActionResult:
        return await self._call("set_group_admin", {"group_id": group_id, "user_id": user_id, "enable": enable})

    async def set_group_name(self, group_id: int, group_name: str) -> ActionResult:
        return await self._call("set_group_name", {"group_id": group_id, "group_name": group_name})

    async def set_group_leave(self, group_id: int, is_dismiss: bool = False) -> ActionResult:
        return await self._call("set_group_leave", {"group_id": group_id, "is_dismiss": is_dismiss})

    async def set_group_special_title(self, group_id: int, user_id: int, special_title: str = "", duration: int = -1) -> ActionResult:
        return await self._call("set_group_special_title", {"group_id": group_id, "user_id": user_id, "special_title": special_title, "duration": duration})

    async def set_friend_add_request(self, flag: str, approve: bool = True, remark: str = None) -> ActionResult:
        params = {"flag": flag, "approve": approve}
        if remark:
            params["remark"] = remark
        return await self._call("set_friend_add_request", params)

    async def set_group_add_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = None) -> ActionResult:
        params = {"flag": flag, "sub_type": sub_type, "approve": approve}
        if reason:
            params["reason"] = reason
        return await self._call("set_group_add_request", params)

    async def get_guild_list(self) -> ActionResult:
        return await self._call_no_params("get_guild_list")

    async def get_guild_channel_list(self, guild_id: int) -> ActionResult:
        return await self._call("get_guild_channel_list", {"guild_id": guild_id})

    async def get_guild_member_list(self, guild_id: int) -> ActionResult:
        return await self._call("get_guild_member_list", {"guild_id": guild_id})

    async def get_guild_member_info(self, guild_id: int, user_id: int) -> ActionResult:
        return await self._call("get_guild_member_info", {"guild_id": guild_id, "user_id": user_id})

    async def get_group_file_url(self, group_id: int, file_id: str, busid: int) -> ActionResult:
        return await self._call("get_group_file_url", {"group_id": group_id, "file_id": file_id, "busid": busid})

    async def get_group_file_list(self, group_id: int, folder: str = None) -> ActionResult:
        params = {"group_id": group_id}
        if folder:
            params["folder"] = folder
        return await self._call("get_group_file_list", params)

    async def get_group_root_files(self, group_id: int) -> ActionResult:
        return await self._call("get_group_root_files", {"group_id": group_id})

    async def get_group_folder_list(self, group_id: int) -> ActionResult:
        return await self._call("get_group_folder_list", {"group_id": group_id})

    async def create_group_file_folder(self, group_id: int, name: str, parent_id: str = "/") -> ActionResult:
        return await self._call("create_group_file_folder", {"group_id": group_id, "name": name, "parent_id": parent_id})

    async def delete_group_folder(self, group_id: int, folder_id: str) -> ActionResult:
        return await self._call("delete_group_folder", {"group_id": group_id, "folder_id": folder_id})

    async def delete_group_file(self, group_id: int, file_id: str, busid: int) -> ActionResult:
        return await self._call("delete_group_file", {"group_id": group_id, "file_id": file_id, "busid": busid})

    async def upload_group_file(self, group_id: int, file: str, name: str, folder: str = None) -> ActionResult:
        params = {"group_id": group_id, "file": file, "name": name}
        if folder:
            params["folder"] = folder
        return await self._call("upload_group_file", params)

    async def upload_group_file_async(self, group_id: int, file: str, name: str, folder: str = None) -> ActionResult:
        params = {"group_id": group_id, "file": file, "name": name}
        if folder:
            params["folder"] = folder
        return await self._call("upload_group_file_async", params)

    async def download_file(self, url: str, thread_count: int = 1, headers: Dict[str, str] = None) -> ActionResult:
        params = {"url": url, "thread_count": thread_count}
        if headers:
            params["headers"] = headers
        return await self._call("download_file", params)

    async def get_file(self, service: str, id: str) -> ActionResult:
        return await self._call("get_file", {"service": service, "id": id})

    async def get_group_system_msg(self) -> ActionResult:
        return await self._call_no_params("get_group_system_msg")

    async def get_essence_msg_list(self, group_id: int) -> ActionResult:
        return await self._call("get_essence_msg_list", {"group_id": group_id})

    async def set_essence_msg(self, message_id: int) -> ActionResult:
        return await self._call("set_essence_msg", {"message_id": message_id})

    async def delete_essence_msg(self, message_id: int) -> ActionResult:
        return await self._call("delete_essence_msg", {"message_id": message_id})

    async def get_gank(self, plugin: str = "单图片", count: int = 1) -> ActionResult:
        return await self._call("get_gank", {"plugin": plugin, "count": count})

    async def get_setu(self, quality: int = 10) -> ActionResult:
        return await self._call("get_setu", {"quality": quality})

    async def get_bing_wallpaper(self) -> ActionResult:
        return await self._call_no_params("get_bing_wallpaper")

    async def send_like(self, user_id: int, times: int = 1) -> ActionResult:
        return await self._call("send_like", {"user_id": user_id, "times": times})

    async def get_vip_info(self, user_id: int) -> ActionResult:
        return await self._call("get_vip_info", {"user_id": user_id})

    async def get_coin_info(self) -> ActionResult:
        return await self._call_no_params("get_coin_info")

    async def send_coin(self, user_id: int, coin_type: str, count: int) -> ActionResult:
        return await self._call("send_coin", {"user_id": user_id, "coin_type": coin_type, "count": count})

    async def get_cookies(self, domain: str = "qq.com") -> ActionResult:
        return await self._call("get_cookies", {"domain": domain})

    async def get_csrf_token(self) -> ActionResult:
        return await self._call_no_params("get_csrf_token")

    async def get_credentials(self, domain: str = "qq.com") -> ActionResult:
        return await self._call("get_credentials", {"domain": domain})

    async def get_record(self, file: str, out_format: str = "mp3") -> ActionResult:
        return await self._call("get_record", {"file": file, "out_format": out_format})

    async def ocr_image(self, image: str) -> ActionResult:
        return await self._call("ocr_image", {"image": image})

    async def translate_google(self, text: str, from_lang: str = "auto", to_lang: str = "zh") -> ActionResult:
        return await self._call("translate_google", {"text": text, "from_lang": from_lang, "to_lang": to_lang})

    async def get_model_show(self, model: str = None) -> ActionResult:
        params = {}
        if model:
            params["model"] = model
        return await self._call("get_model_show", params)

    async def set_model_show(self, model: str) -> ActionResult:
        return await self._call("set_model_show", {"model": model})

    async def _get_api_list(self) -> List[str]:
        apis = [
            "get_login_info", "get_version_info", "get_status", "set_qq_profile", "set_self_status", "clean_cache",
            "get_stranger_info", "get_friend_list", "get_friend_info",
            "get_group_list", "get_group_info", "get_group_member_list", "get_group_member_info", "get_group_honor_info",
            "send_msg", "send_private_msg", "send_group_msg", "send_msg_ex", "delete_msg", "get_msg", "get_forward_msg",
            "send_group_forward_msg", "send_group_forward_msg_ex", "get_image", "can_send_image", "can_send_record",
            "set_group_kick", "set_group_ban", "set_group_whole_ban", "set_group_admin", "set_group_name", "set_group_leave",
            "set_group_special_title", "set_friend_add_request", "set_group_add_request",
            "get_guild_list", "get_guild_channel_list", "get_guild_member_list", "get_guild_member_info",
            "get_group_file_url", "get_group_file_list", "get_group_root_files", "get_group_folder_list",
            "create_group_file_folder", "delete_group_folder", "delete_group_file",
            "upload_group_file", "upload_group_file_async", "download_file", "get_file",
            "get_group_system_msg", "get_essence_msg_list", "set_essence_msg", "delete_essence_msg",
            "get_gank", "get_setu", "get_bing wallpaper", "send_like",
            "get_vip_info", "get_coin_info", "send_coin", "get_cookies", "get_csrf_token", "get_credentials",
            "get_record", "ocr_image", "translate_google", "get_model_show", "set_model_show",
        ]
        return apis

    async def call_api(self, action: str, params: Dict[str, Any] = None) -> ActionResult:
        return await self._call(action, params)

class RuntimeBundle:
    def __init__(self):
        self.transport: Optional[NapCatTransportClient] = None
        self.action_service: Optional[NapCatActionService] = None
        self.codec = None
        self.router = None
