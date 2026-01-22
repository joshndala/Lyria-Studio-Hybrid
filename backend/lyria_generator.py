import os
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value
from google.oauth2 import service_account  # Required for manual credential loading

# Configuration
MODEL_ID = 'lyria-002'
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION", "us-central1")
CREDENTIALS_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

async def generate_music_file(
        prompt: str,
        negative_prompt: str = "",
        seed: int = None,
        output_filename: str = "temp_music.wav"
) -> str:
    """Generates high-fidelity audio using Lyria-002 with explicit credentials."""
    
    # 1. Validate Credentials Path
    if not CREDENTIALS_PATH or not os.path.exists(CREDENTIALS_PATH):
        raise ValueError(f"Credentials file not found at: {CREDENTIALS_PATH}")

    print(f"Requesting music generation from {MODEL_ID}...")

    try:
        # 2. Manually load the Service Account credentials
        # This ensures the script uses the specific permissions of your service account
        creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH)
        
        # 3. Initialize Vertex AI with these credentials
        aiplatform.init(
            project=PROJECT_ID, 
            location=LOCATION, 
            credentials=creds
        )

        # 4. Initialize the Prediction Client with explicit credentials and regional endpoint
        client_options = {"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
        predict_client = aiplatform.gapic.PredictionServiceClient(
            client_options=client_options,
            credentials=creds  # CRITICAL: This fixes the 403 error
        )

        # The endpoint for Lyria-002 (Publisher Model)
        endpoint_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_ID}"
        
        # 5. Prepare Instance Schema
        instance_dict = {"prompt": prompt}
        if negative_prompt:
            instance_dict["negative_prompt"] = negative_prompt
        if seed is not None:
            instance_dict["seed"] = int(seed)

        instance = json_format.ParseDict(instance_dict, Value())

        # 6. Prepare Parameters (sample_count is 1-4, but cannot be used with a seed)
        parameters_dict = {}
        if seed is None:
            parameters_dict["sample_count"] = 1
            
        parameters = json_format.ParseDict(parameters_dict, Value())

        # 7. Make the prediction request
        response = predict_client.predict(
            endpoint=endpoint_path, 
            instances=[instance], 
            parameters=parameters
        )

        # 8. Handle the response using the 'audioContent' key
        if not response.predictions:
            raise ValueError("No predictions returned from model.")

        for i, prediction in enumerate(response.predictions):
            # Access the underlying dictionary from the Protobuf Value
            # Lyria 2 specifically uses the key 'audioContent'
            audio_data_b64 = prediction.get("bytesBase64Encoded")
            
            if audio_data_b64:
                audio_bytes = base64.b64decode(audio_data_b64)
                
                # Append index if multiple samples were generated
                final_name = f"{i}_{output_filename}" if len(response.predictions) > 1 else output_filename
                
                with open(final_name, "wb") as f:
                    f.write(audio_bytes)
                
                print(f"Success! Music saved to {final_name}")
                return final_name
            else:
                # Print keys to help debug if Google changes the schema
                print(f"Available keys in response: {list(prediction.keys())}")
                raise ValueError("Field 'audioContent' missing in prediction response.")

    except Exception as e:
        print(f"API Error: {e}")
        return None