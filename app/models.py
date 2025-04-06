from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Optional


class Schedule(BaseModel):
    morning: Optional[List[str]] = []
    afternoon: Optional[List[str]] = []
    evening: Optional[List[str]] = []


class DoctorModel(BaseModel):
    doctor_id: str
    name: str
    gender: str
    years_of_experience: int
    degrees: List[str]
    languages_spoken: List[str]
    bio: str
    primary_specialization: str
    treatable_conditions: List[str]
    location: str
    distance_km: str  # You can make this float/int if you normalize "<50"
    hospital_affiliation: str
    consultation_modes: List[str]
    consultation_fee_usd: float
    ratings: float
    number_of_reviews: int
    accepting_new_patients: bool
    profile_image_url: HttpUrl
    medical_philosophy: str
    weekly_schedule: Dict[str, Schedule]

class UserLogin(BaseModel)
    username: str,
    password: str

class UserModel(BaseModel):
    patient_id: str
    password: str
    age: int
    gender: str
    location: str
    profile_image_url: HttpUrl