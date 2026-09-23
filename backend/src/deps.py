from typing import Annotated

from fastapi import Depends

from src.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]
