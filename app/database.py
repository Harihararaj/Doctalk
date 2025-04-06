from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "doctalk_hags1"
COLLECTION_NAME = "doctor"
COLLECTION_USER_LOGIN="user_login"

def create_mongo_client():
    client = AsyncIOMotorClient(MONGO_URI)
    return client