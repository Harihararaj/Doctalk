import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent

# === Load API Key ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# === State Tracking ===
last_specialization = {"value": None}
last_selected_doctor_id = {"id": None}
doctor_cache = {"data": []}

# === Tool 1: Diagnose Specialization ===


@tool
def diagnose_specialization(symptom: str) -> str:
    """Infers the medical specialization based on a symptom."""
    prompt = f"""
    A patient describes their issue as: '{symptom}'.
    Based on this symptom, identify the most appropriate medical specialization from this list:
    - ENT, General Physician, Obstetrics & Gynaecology, Paediatrics, Orthopaedics, Dermatology, Urology, Neurology, Cardiology
    Just return the specialization only.
    """
    llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
    response = llm.invoke(prompt)
    specialization = response.content.strip().replace("specialist", "").strip()
    last_specialization["value"] = specialization
    return f"You may need a {specialization} specialist. Would you like me to find top doctors?"

# === Tool 2: Show Top 5 Doctors (name + ID) ===


@tool
def get_top_doctor_names(specialization: str) -> str:
    """Fetches and shows only the top 5 doctors (name + ID) from the backend."""
    try:
        url = f"http://192.168.0.96:8000/get_doctors/{specialization}"
        response = requests.get(url)
        response.raise_for_status()
        doctors = response.json()
        doctor_cache["data"] = doctors

        if not doctors:
            return "No doctors found for that specialization."

        sorted_docs = sorted(doctors, key=lambda d: (
            d["ratings"], d["years_of_experience"]), reverse=True)

        top_5 = sorted_docs[:5]
        doctor_cache["data"] = top_5

        output = "Here are the top 5 doctors:\n\n"
        for i, doc in enumerate(top_5, 1):
            output += f"{i}. {doc['name']} (ID: {doc['doctor_id']})\n"
        output += "\nPlease enter the Doctor ID to view the schedule."
        return output

    except requests.RequestException as e:
        return f"❌ Error fetching doctors: {e}"

# === Tool 3: Show Weekly Schedule by Doctor ID ===


@tool
def get_doctor_schedule_by_id(doctor_id: str) -> str:
    """Shows the schedule for the selected doctor by ID."""
    for doc in doctor_cache["data"]:
        if doc["doctor_id"].lower() == doctor_id.lower():
            last_selected_doctor_id["id"] = doc["doctor_id"]
            schedule = doc.get("weekly_schedule", {})
            lines = []
            for day, times in schedule.items():
                lines.append(f"{day}: {', '.join(times)}")
            return f"Availability for {doc['name']} (ID: {doctor_id}):\n" + "\n".join(lines)
    return "❌ Doctor ID not found in the top 5 list."



def book_slot(doctor_id: str, day: str, time: str) -> str:
    try:
        payload = {
            "doctor_id": doctor_id,
            "day": day,
            "time": time
        }
        res = requests.post(
            "http://192.168.0.96:8000/delete_availability/", json=payload)
        if res.status_code == 200:
            return f"✅ Appointment booked with Doctor {doctor_id} on {day} at {time}."
        return f"❌ Failed to book appointment: {res.text}"
    except Exception as e:
        return f"❌ Booking error: {str(e)}"


# === LangChain Agent ===
llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
tools = [diagnose_specialization,
         get_top_doctor_names, get_doctor_schedule_by_id]
memory = ConversationBufferMemory(
    memory_key="chat_history", return_messages=True)
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent="openai-functions",
    memory=memory,
    verbose=True
)

# === Chat Loop ===
if __name__ == "__main__":
    print("👩‍⚕️ Hello! I'm your AI medical assistant.")
    print("🩺 Describe your symptoms and I’ll help you find a doctor and book an appointment.")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        # Case 1: Show doctors
        elif user_input.lower() in ["yes", "ok", "sure"] and last_specialization["value"]:
            response = get_top_doctor_names.run(last_specialization["value"])

        # Case 2: Doctor ID selection
        elif any(doc["doctor_id"].lower() in user_input.lower() for doc in doctor_cache["data"]):
            matched = next((doc["doctor_id"] for doc in doctor_cache["data"]
                           if doc["doctor_id"].lower() in user_input.lower()), None)
            response = get_doctor_schedule_by_id.run(matched)

        # Case 3: Booking
        elif last_selected_doctor_id["id"]:
            match = re.search(
                r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)[\s,:-]*([0-9]{1,2})([:.][0-9]{2})?(?:\s*(am|pm))?",
                user_input.lower()
            )
            if match:
                try:
                    day = match.group(1).capitalize()
                    hour = match.group(2)
                    minute = match.group(3) if match.group(3) else ":00"
                    meridian = match.group(4)

                    time_raw = hour + minute
                    if meridian:
                        time_obj = datetime.strptime(
                            time_raw + meridian, "%I:%M%p")
                    else:
                        time_obj = datetime.strptime(time_raw, "%H:%M")
                    time = time_obj.strftime("%H:%M")

                    response = book_slot(
                        last_selected_doctor_id["id"], day, time)
                    print("Bot:", response)

                    follow_up = input(
                        "Bot: Would you like help with anything else?\nYou: ").strip().lower()
                    if follow_up in ["no", "exit", "quit", "nah", "nope"]:
                        print("👋 Okay! Take care and feel better soon.")
                        break
                    continue
                except Exception as e:
                    response = f"❌ Error processing booking: {e}"
            else:
                response = agent_executor.invoke(
                    {"input": user_input})["output"]

        # Case 4: Default to LLM
        else:
            response = agent_executor.invoke({"input": user_input})["output"]

        print("Bot:", response)
