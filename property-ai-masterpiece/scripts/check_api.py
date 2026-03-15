import requests

r = requests.get("http://localhost:8000/health")
print("Health:", r.json())

r2 = requests.get("http://localhost:8000/api/v1/stats")
d = r2.json()
print(f"Total images: {d['total_images']}, Real: {d['real_images']}, Fake: {d['fake_images']}")
print(f"Avg quality: {d['avg_quality_score']}, Avg trust: {d['avg_trust_score']}")
print("Top room types:", list(d['room_type_distribution'].items())[:3])
