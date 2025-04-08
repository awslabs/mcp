from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Switch(Base):
    __tablename__ = "switches"
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, unique=True, index=True)
    nome = Column(String)
    status = Column(String)

class LogComando(Base):
    __tablename__ = "logs_comandos"
    id = Column(Integer, primary_key=True, index=True)
    switch_id = Column(Integer, ForeignKey("switches.id"))
    comando = Column(String)
    usuario = Column(String)
    data_execucao = Column(DateTime)