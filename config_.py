from nonebot import get_driver
from pydantic import BaseModel

class Config(BaseModel):
    token: str
    refresh_token:str
    assistant_id:str
    timeout: int = 60
    max_len: int = 200
    preset_path: str = "./data/chatglm/preset.json"

config = Config.parse_obj(get_driver().config)
