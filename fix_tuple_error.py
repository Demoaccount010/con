import os

# Files to scan for the missing Tuple import
files_to_check = [
    "main_agent/ollama/client.py",
    "main_agent/ollama/models.py",
    "main_agent/doctor/healer.py",
    "main_agent/workers/dispatcher.py"
]

def fix_file(filepath):
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        modified = False
        
        for line in lines:
            # Check if line has imports from typing but missing Tuple
            if "from typing import" in line and "Tuple" not in line:
                # Add Tuple to the import list safely
                line = line.strip() + ", Tuple\n"
                modified = True
            new_lines.append(line)

        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(f"✅ Fixed: {filepath}")
        else:
            print(f"ℹ️  No changes needed: {filepath}")

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")

# Run the fix
print("🔍 Scanning and fixing missing 'Tuple' imports...")
for file in files_to_check:
    fix_file(file)

print("\n✨ All done! Now try running launcher.py again.")
