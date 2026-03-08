from .base import Base
from .session import engine
from . import models  # noqa: F401

def init_db(auto_create: bool = False):
    if auto_create:
        Base.metadata.create_all(bind=engine)