"""FastAPI backend. The presence of `app = FastAPI()` at module level is the
canonical signal StructureAnalyzer uses to classify as fastapi-api."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.get("/items/{item_id}")
def read_item(item_id: int) -> Item:
    return Item(name=f"item-{item_id}", price=1.0)
