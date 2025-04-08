from fastapi import FastAPI, Depends, HTTPException
from .database import SessionLocal, engine
from . import models, schemas, crud
from sqlalchemy.orm import Session

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependência para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/usuarios/", response_model=schemas.Usuario)
def criar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = crud.get_usuario(db, username=usuario.username)
    if db_usuario:
        raise HTTPException(status_code=400, detail="Usuário já existe")
    return crud.criar_usuario(db, usuario=usuario)