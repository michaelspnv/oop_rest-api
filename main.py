import os
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Boolean

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    id=Column(Integer, primary_key=True)
    text=Column(String)
    is_done=Column(Boolean, default=False)

load_dotenv()

url = (f"postgresql://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@"
       f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")

engine = create_engine(url)
Session = sessionmaker(bind=engine)
session = Session()

Base.metadata.create_all(engine)

app = FastAPI()

@app.get("/")
async def get_all_todos():
    todos_query = session.query(Item)
    return todos_query.all()

@app.put("/update/{id}")
async def update_todo(id: int, new_text: str = "", is_complete: bool = False):
    todo_query = session.query(Item).filter(Item.id == id)
    todo = todo_query.first()
    if new_text:
        todo.text = new_text
    todo.is_done = is_complete
    session.add(todo)
    session.commit()
    return {"todo updated": todo.id}

@app.post("/create")
async def create_todo(text: str, is_complete: bool = False):
    todo_item = Item(text=text, is_done=is_complete)
    session.add(todo_item)
    session.commit()
    return {"todo added": todo_item.text}

@app.delete("/delete/{id}")
async def delete_todo(id: int):
    todo = session.query(Item).filter(Item.id == id).first()
    session.delete(todo)
    session.commit()
    return {"todo deleted": todo.text}