from pydantic import BaseModel
from datetime import datetime

class UsuarioBase(BaseModel):
    username: str

class UsuarioCreate(UsuarioBase):
    password: str

class Usuario(UsuarioBase):
    id: int

    class Config:
        orm_mode = True

class SwitchBase(BaseModel):
    ip: str
    nome: str

class SwitchCreate(SwitchBase):
    pass

class Switch(SwitchBase):
    id: int
    status: str

    class Config:
        orm_mode = True

class LogComandoBase(BaseModel):
    comando: str
    usuario: str

class LogComandoCreate(LogComandoBase):
    pass

class LogComando(LogComandoBase):
    id: int
    data_execucao: datetime

    class Config:
        orm_mode = True