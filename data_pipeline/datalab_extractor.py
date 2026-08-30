import os
from pathlib import Path

from datalab_sdk import DatalabClient
from datalab_sdk.exceptions import (
    DatalabAPIError,
    DatalabFileError,
    DatalabTimeoutError,
    DatalabValidationError,
)
from dotenv import load_dotenv

load_dotenv()
DATALAB_API_KEY = os.getenv("DATALAB_API_KEY")
OUTPUT_DIR = "extracted_pdf_contents"
INPUT_DIR = "raw_pdfs"

directory = Path(INPUT_DIR)
# Use is_file() to filter out folders/directories
files = [f.name for f in directory.iterdir() if f.is_file()]
print(files)


client = DatalabClient(api_key=DATALAB_API_KEY)

for filename in files[1:]:
    try:
        result = client.convert(f"raw_pdfs/{filename}")
    except DatalabAPIError as e:
        print(f"API error {e.status_code}: {e.response_data}")
    except DatalabTimeoutError:
        print("Request timed out")
    except DatalabFileError as e:
        print(f"File error: {e}")
    except DatalabValidationError as e:
        print(f"Invalid input: {e}")

    print(f"Converted File {filename}")
    result.save_output(f"{OUTPUT_DIR}/{filename}")
    print(f"Converted File {filename} and saved")


print("All done")
