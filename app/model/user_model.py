from sqlmodel import Field

from app.model.base_model import BaseModel


class UserModel(BaseModel, table=True):
    __tablename__ = "tb_users"

    username: str = Field(index=True, nullable=False, unique=True)
    password_hash: str = Field(nullable=False)


# đây là cái cái liên kết giữa cái model với database
