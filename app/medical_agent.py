import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain_core.runnables import RunnablePassthrough
from langchain.agents import AgentExecutor
from langchain.tools.render import format_tool_to_openai_function

# === Load OpenAI API Key ===
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# === Shared State ===
last_specialization = {"value": None}
last_selected_doctor_id = {"id": None}
doctor_cache = {"data": []}

# === Tool 1: Diagnose Specialization ===
@tool
def diagnose_specialization(symptom: str) -> str:
    """Infers the medical specialization based on a symptom."""
    prompt = f"""
    A patient describes their issue as: '{symptom}'.
    Based on this symptom, identify the most appropriate medical specialization from:
    ENT, General Physician, Obstetrics & Gynaecology, Paediatrics, Orthopaedics,
    Dermatology, Urology, Neurology, Cardiology.
    Just return the specialization only.
    """
    llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
    response = llm.invoke(prompt)
    specialization = response.content.strip().replace("specialist", "").strip()
    last_specialization["value"] = specialization
    return f"You may need a {specialization} specialist. Would you like me to find top doctors?"

# === Tool 2: Top Doctors ===
@tool
def get_top_doctor_names(specialization: str) -> str:
    """Fetches and shows top 5 doctors (name + ID) from backend."""
    try:
        url = f"http://192.168.0.96:8000/get_doctors/{specialization}"
        response = requests.get(url)
        response.raise_for_status()
        doctors = response.json()
        doctor_cache["data"] = doctors

        if not doctors:
            return "No doctors found for that specialization."

        sorted_docs = sorted(doctors, key=lambda d: (d["ratings"], d["years_of_experience"]), reverse=True)
        top_5 = sorted_docs[:5]
        doctor_cache["data"] = top_5

        output = "Here are the top 5 doctors:\n\n"
        for i, doc in enumerate(top_5, 1):
            output += f"{i}. {doc['name']} (ID: {doc['doctor_id']})\n"
        output += "\nPlease enter the Doctor ID to view the schedule."
        return output

    except requests.RequestException as e:
        return f"❌ Error fetching doctors: {e}"

# === Tool 3: Doctor Schedule ===
@tool
def get_doctor_schedule_by_id(doctor_id: str) -> str:
    """Returns the weekly schedule for a given doctor ID."""
    for doc in doctor_cache["data"]:
        if doc["doctor_id"].lower() == doctor_id.lower():
            last_selected_doctor_id["id"] = doc["doctor_id"]
            schedule = doc.get("weekly_schedule", {})
            lines = []
            for day, times in schedule.items():
                lines.append(f"{day}: {', '.join(times)}")
            return f"Availability for {doc['name']} (ID: {doctor_id}):\n" + "\n".join(lines)
    return "❌ Doctor ID not found in the top 5 list."

# === Tool 4: Book Appointment ===
@tool
def book_appointment_slot(query: str) -> str:
    """Books a slot if doctor ID is selected and time format is correct."""
    if not last_selected_doctor_id["id"]:
        return "❗ Please select a doctor first."

    match = re.search(
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)[\s,:-]*(?:at\s*)?([0-9]{1,2})([:.][0-9]{2})?\s*(am|pm)?",
        query.lower()
    )
    if not match:
        return "❗ Could not extract booking day/time. Try again."

    try:
        day = match.group(1).capitalize()
        hour = match.group(2)
        minute = match.group(3) if match.group(3) else ":00"
        meridian = match.group(4)
        time_raw = hour + minute

        if meridian:
            time_obj = datetime.strptime(time_raw + meridian, "%I:%M%p")
        else:
            time_obj = datetime.strptime(time_raw, "%H:%M")
        time = time_obj.strftime("%H:%M")

        payload = {
            "doctor_id": last_selected_doctor_id["id"],
            "day": day,
            "time": time
        }
        res = requests.post("http://192.168.0.96:8000/delete_availability/", json=payload)
        if res.status_code == 200:
            return f"✅ Appointment booked with Doctor {last_selected_doctor_id['id']} on {day} at {time}."
        return f"❌ Failed to book appointment: {res.text}"
    except Exception as e:
        return f"❌ Error booking appointment: {str(e)}"

# === Build AgentExecutor with agentfinish ===
tools = [diagnose_specialization, get_top_doctor_names, get_doctor_schedule_by_id, book_appointment_slot]
functions = [format_tool_to_openai_function(t) for t in tools]

llm = ChatOpenAI(model="gpt-4o", api_key=api_key).bind(functions=functions)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI medical assistant."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

chain = RunnablePassthrough.assign(
    agent_scratchpad=lambda x: format_to_openai_functions(x["intermediate_steps"])
) | prompt | llm | OpenAIFunctionsAgentOutputParser()

memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")

agent_executor = AgentExecutor(
    agent=chain,
    tools=tools,
    verbose=True,
    memory=memory
)
