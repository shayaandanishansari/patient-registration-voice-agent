from typing import Annotated

from fastapi import Depends, Request

from app.db import Database


def get_db(request: Request) -> Database:
    return request.app.state.db


DbDep = Annotated[Database, Depends(get_db)]
