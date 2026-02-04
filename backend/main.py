import sys
import os
from pathlib import Path

# Add project root and app directory to path
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))
sys.path.append(str(root_path / "app"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.content_generator import ContentGenerator
from app.data_models import ProcessedInput, InputType

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Generator
# Note: We are using the default initialization which prioritizes Local Models and falls back to Mock
generator = ContentGenerator()

class GenerateRequest(BaseModel):
    content: str
    inputType: str = "text" # text, audio, etc.

@app.get("/")
def read_root():
    return {"status": "online", "message": "ECHOVERSA Backend Running"}

@app.post("/api/generate")
def generate_response(request: GenerateRequest):
    try:
        # Convert request to data_models.ProcessedInput
        itype = InputType.TEXT
        if request.inputType.lower() == "audio":
            itype = InputType.AUDIO
            
        input_data = ProcessedInput(
            content=request.content,
            input_type=itype
        )
        
        # generate_support_and_poem returns a GeneratedContent object
        result = generator.generate_support_and_poem(input_data)
        
        return {
            "supportive_statement": result.supportive_statement,
            "poem": result.poem,
            "metadata": result.generation_metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
def get_config():
    """Returns info about the current AI model being used."""
    # Check if Gemini or OpenAI is active (though code currently disables it)
    is_openai = False
    model_name = generator.get_current_generator_name()
    
    # Simple check for 'gpt' or 'gemini' in name just in case
    if "gemini" in model_name.lower() or "gpt" in model_name.lower():
        is_openai = True

    return {
        "model_name": model_name,
        "available_generators": generator.get_available_generators(),
        "is_using_openai": is_openai,
        "disclaimer": "This system operates using Local AI models. Your data remains private." if not is_openai else "This system utilizes external AI APIs."
    }
