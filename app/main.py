from typing import Union
from .database import create_mongo_client, DB_NAME, COLLECTION_NAME
from fastapi import FastAPI, Request
import json

app = FastAPI()

@app.on_event("startup")
async def startup_db_client():
    app.state.mongo_client = create_mongo_client()
    app.state.db = app.state.mongo_client[DB_NAME]
    app.state.item_collection = app.state.db[COLLECTION_NAME]

@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.mongo_client.close()

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None, request: Request = None):
    item_collection = request.app.state.item_collection

    with open('/Users/harihararajjayabalan/Documents/Hackethon/Doctalk/app/doc.json', 'r') as file:
        doctors = json.load(file)
    result = await item_collection.insert_many(doctors)
    return {"inserted_ids": [str(id) for id in result.inserted_ids]}

