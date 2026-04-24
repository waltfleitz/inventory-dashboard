import json

with open("chevy_new.json", "r") as f:
    data = json.load(f)

# Deduplicate by BAC
seen = set()
cleaned = []

for d in data:
    bac = str(d.get("bac", "")).strip()

    if bac and bac not in seen:
        seen.add(bac)
        cleaned.append(d)

with open("chevy_dealers_master.json", "w") as f:
    json.dump(cleaned, f, indent=2)

print(f"✅ Rebuilt Chevy master: {len(cleaned)} dealers")