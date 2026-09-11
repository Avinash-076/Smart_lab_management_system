import json
import os

from config import OUTPUT_FOLDER


def export_to_json(data, filename="client_data.json"):

    # Create output folder if it doesn't exist
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    filepath = os.path.join(OUTPUT_FOLDER, filename)

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    return filepath