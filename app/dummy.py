import requests

response = requests.post("http://localhost:8000/delete_availability/", params={
    "doctor_id": "D0024",
    "day": "monday",
    "time": "10:00"
})

print(response.status_code)
print(response.json())