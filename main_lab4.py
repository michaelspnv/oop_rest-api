import os
from datetime import datetime
from typing import List
from fastapi import FastAPI, Depends, APIRouter
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ToDoList(Base):
    __tablename__ = "todo_lists"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    deleted_at = Column(DateTime, nullable=True)

    items = relationship("Item", back_populates="todo_list")

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    text = Column(String)
    is_done = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    todo_list_id = Column(Integer, ForeignKey("todo_lists.id"))

    todo_list = relationship("ToDoList", back_populates="items")

class ToDoService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_lists(self):
        lists = self.db.query(ToDoList).filter(ToDoList.deleted_at.is_(None)).all()
        return [{
            "id": l.id,
            "name": l.name,
            "progress": int((l.completed_items / l.total_items) * 100) if l.total_items > 0 else 0
        } for l in lists]

    def create_list(self, name: str):
        new_list = ToDoList(name=name)
        self.db.add(new_list)
        self.db.commit()
        return new_list

    def create_item(self, text: str, list_id: int, is_complete: bool = False):
        item = Item(text=text, is_done=is_complete, todo_list_id=list_id)
        self.db.add(item)

        todo_list = self.db.query(ToDoList).filter(ToDoList.id == list_id, ToDoList.deleted_at.is_(None)).first()
        if todo_list:
            todo_list.total_items += 1
            if is_complete:
                todo_list.completed_items += 1
            self.db.add(todo_list)

        self.db.commit()
        return item

    def update_item(self, item_id: int, new_text: str, is_complete: bool):
        item = self.db.query(Item).filter(Item.id == item_id, Item.deleted_at.is_(None)).first()
        if not item:
            return None

        if new_text:
            item.text = new_text

        if item.is_done != is_complete:
            delta = 1 if is_complete else -1
            if item.todo_list:
                item.todo_list.completed_items += delta
                self.db.add(item.todo_list)

        item.is_done = is_complete
        self.db.add(item)
        self.db.commit()
        return item

    def delete_item(self, item_id: int):
        item = self.db.query(Item).filter(Item.id == item_id, Item.deleted_at.is_(None)).first()
        if not item:
            return None

        item.deleted_at = datetime.utcnow()
        if item.todo_list:
            item.todo_list.total_items -= 1
            if item.is_done:
                item.todo_list.completed_items -= 1
            self.db.add(item.todo_list)

        self.db.add(item)
        self.db.commit()
        return item

    def delete_list(self, list_id: int):
        todo_list = self.db.query(ToDoList).filter(ToDoList.id == list_id, ToDoList.deleted_at.is_(None)).first()
        if not todo_list:
            return None

        todo_list.deleted_at = datetime.utcnow()
        for item in todo_list.items:
            item.deleted_at = datetime.utcnow()
            self.db.add(item)

        self.db.add(todo_list)
        self.db.commit()
        return todo_list

def get_service():
    db = SessionLocal()
    try:
        yield ToDoService(db)
    finally:
        db.close()

router = APIRouter()

@router.get("/")
def get_all_lists(service: ToDoService = Depends(get_service)):
    return service.get_all_lists()

@router.post("/create_list")
def create_list(name: str, service: ToDoService = Depends(get_service)):
    return {"todo_list added": service.create_list(name).name}

@router.post("/create_item")
def create_item(text: str, list_id: int, is_complete: bool = False, service: ToDoService = Depends(get_service)):
    return {"todo added": service.create_item(text, list_id, is_complete).text}

@router.put("/update/{id}")
def update_item(id: int, new_text: str = "", is_complete: bool = False, service: ToDoService = Depends(get_service)):
    updated = service.update_item(id, new_text, is_complete)
    return {"todo updated": updated.id} if updated else {"error": "Item not found"}

@router.delete("/delete_item/{id}")
def delete_item(id: int, service: ToDoService = Depends(get_service)):
    deleted = service.delete_item(id)
    return {"todo soft-deleted": deleted.text} if deleted else {"error": "Item not found"}

@router.delete("/delete_list/{id}")
def delete_list(id: int, service: ToDoService = Depends(get_service)):
    deleted = service.delete_list(id)
    return {"todo list soft-deleted": deleted.name} if deleted else {"error": "ToDoList not found"}

def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    app = FastAPI()
    app.include_router(router)
    return app

app = create_app()
