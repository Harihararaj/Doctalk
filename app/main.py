from typing import Union
from .database import create_mongo_client, DB_NAME, COLLECTION_NAME, COLLECTION_USER_LOGIN
from fastapi import FastAPI, Request
import json
from .medical_agent import agent_executor

app = FastAPI()


@app.on_event("startup")
async def startup_db_client():
    app.state.mongo_client = create_mongo_client()
    app.state.db = app.state.mongo_client[DB_NAME]
    app.state.item_collection = app.state.db[COLLECTION_NAME]
    app.state.login_collection = app.state.db[COLLECTION_USER_LOGIN]

@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.mongo_client.close()

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/populate_json/")
async def populate_json(request: Request = None):
    item_collection = request.app.state.item_collection

    with open('/Users/harihararajjayabalan/Documents/Hackethon/Doctalk/app/doc.json', 'r') as file:
        doctors = json.load(file)
    result = await item_collection.insert_many(doctors)
    return {"inserted_ids": [str(id) for id in result.inserted_ids]}

# utils.py

from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorCollection

async def fetch_doctors_by_specialization(
    collection: AsyncIOMotorCollection, specialization: str
) -> List[Dict]:
    doctors = []
    cursor = collection.find({'primary_specialization': {"$regex": specialization, "$options": "i"}})
    async for doc in cursor:
        doctors.append({
            "doctor_id": doc["doctor_id"],
            "name": doc["name"],
            "gender": doc["gender"],
            "years_of_experience": doc["years_of_experience"],
            "degrees": doc["degrees"],
            "languages_spoken": doc["languages_spoken"],
            "bio": doc["bio"],
            "primary_specialization": doc["primary_specialization"],
            "treatable_conditions": doc["treatable_conditions"],
            "location": doc["location"],
            "distance_km": doc["distance_km"],
            "hospital_affiliation": doc["hospital_affiliation"],
            "consultation_modes": doc["consultation_modes"],
            "consultation_fee_usd": doc["consultation_fee_usd"],
            "ratings": doc["ratings"],
            "number_of_reviews": doc["number_of_reviews"],
            "accepting_new_patients": doc["accepting_new_patients"],
            "profile_image_url": doc["profile_image_url"],
            "medical_philosophy": doc["medical_philosophy"],
            "weekly_schedule": doc["weekly_schedule"],
        })
    return doctors


@app.get("/get_doctors/{specialization}")
async def get_doctors(specialization: str, request: Request = None):
    item_collection = request.app.state.item_collection
    doctors = await fetch_doctors_by_specialization(item_collection, specialization)
    return doctors

@app.post("/delete_availability/")
async def delete_availability(request: Request = None):
    item_collection = request.app.state.item_collection
    data = await request.json()
    print(data)
    field_to_update = f"weekly_schedule.{data['day']}"
    result = await item_collection.update_one(
        {"doctor_id": data['doctor_id']},
        {"$pull": {field_to_update: data['time']}}
    )
    if result.modified_count == 1:
        return {"status": "success", "message": f"Removed {data['time']} from Monday morning"}
    else:
        return {"status": "not modified", "message": "Time not found or doctor_id invalid"}

@app.post("/check_user/")
async def check_user(request: Request = None):
    login_collection = request.app.state.login_collection
    data = await request.json()
    username = data['username']
    password = data['password']
    result = await login_collection.find_one({
        'username': username,
        'password': password
    })

    if result:
        return {"status": "success", "message": "Login successful"}
    else:
        return {"status": "fail", "message": "Invalid credentials"}

@app.post("/add_user/")
async def add_user(request: Request = None):
    login_collection = request.app.state.login_collection
    data = await request.json()
    username = data['username']
    password = data['password']
    result = await login_collection.insert_one({'username':username, 'password': password})
    if result.inserted_id:
        return {
            "status": "success",
            "user_id": str(result.inserted_id)
        }
    else:
        return {"status": "failed", "message": "User not inserted"}


@app.get("/chat/{prompt}")
def chat_with_agent(prompt: str):
    response = agent_executor.invoke({"input": prompt})
    return {"response": response["output"]}





