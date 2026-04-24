import json

with open("chevy_dealers_master.json", "r", encoding="utf-8") as f:
    content = f.read().strip()

# Fix common issues
if not content.startswith("["):
    content = "[" + content

if not content.endswith("]"):
    content = content + "]"

# Try to load it
data = json.loads(content)

# Save clean version
with open("chevy_dealers_master_fixed.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("✅ JSON fixed and saved as chevy_dealers_master_fixed.json")