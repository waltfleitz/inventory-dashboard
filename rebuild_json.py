import json

fixed = []

with open("chevy_dealers_master.json", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()

        # Skip junk lines
        if not line or line in ["[", "]"]:
            continue

        # Remove trailing commas
        if line.endswith(","):
            line = line[:-1]

        try:
            obj = json.loads(line)
            fixed.append(obj)
        except:
            continue  # skip bad lines

# Save clean JSON
with open("chevy_dealers_master_clean.json", "w", encoding="utf-8") as f:
    json.dump(fixed, f, indent=2)

print(f"✅ Rebuilt JSON with {len(fixed)} dealers")