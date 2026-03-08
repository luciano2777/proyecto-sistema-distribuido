import os
import json

# Define the directory at the top level
script_dir = os.path.dirname(os.path.abspath(__file__))

def load_jsons_as_dictionaries():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    all_data = []

    for filename in os.listdir(script_dir):
        if filename.endswith(".json"):
            file_path = os.path.join(script_dir, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
                
                # --- FILTERING STEP ---
                # Only extract 'id' and 'text'. If keys might be missing, 
                # use .get(key, default) to avoid errors.
                filtered_entry = {
                    "id": full_data.get("id"),
                    "text": full_data.get("text", [])
                }
                all_data.append(filtered_entry)

    # Sort by ID to ensure sequence
    all_data.sort(key=lambda x: x['id'])
    
    return all_data
def reassemble_files():
    # --- Execution ---
    data = load_jsons_as_dictionaries()

    # 1. Displaying findings
    for entry in data:
        print(f"Dictionary found -> ID: {entry['id']}, Content Snippet: {str(entry['text'])[:50]}...")

    # 2. Extracting all text into a single string
    # Since data is a list of dicts, we iterate through the list and join the 'text' list
    full_text_output = ""
    for entry in data:
        # Assuming 'text' is a list of strings based on your original code
        paragraph = "\n\n".join(entry['text'])
        full_text_output += paragraph + "\n\n"

    print("\n--- Final Merged Text ---")
    print(full_text_output)

    output_txt_path = os.path.join(script_dir, "final_output.txt")

    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write(full_text_output)

    print(f"Successfully saved Text to {output_txt_path}")