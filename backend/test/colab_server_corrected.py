from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import nest_asyncio
from pyngrok import ngrok
import uvicorn
import torch

nest_asyncio.apply()

app = FastAPI(title="Colab LLM API")

# Enable CORS for local backend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (use specific domain in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 512  # Changed from max_length to match your backend
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9

class GenerateResponse(BaseModel):
    generated_text: str
    prompt: str

@app.post("/generate", response_model=GenerateResponse)
async def generate(request_body: GenerateRequest):
    try:
        prompt = request_body.prompt
        temperature = request_body.temperature
        max_tokens = request_body.max_tokens
        
        print(f"\n{'='*60}")
        print(f"📝 Received prompt: {prompt[:100]}...")
        print(f"⚙️  Temperature: {temperature}, Max tokens: {max_tokens}")

        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        input_length = inputs['input_ids'].shape[1]
        
        print(f"📊 Input length: {input_length} tokens")

        # Generate with proper parameters to prevent repetition
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,  # Enable sampling
                top_p=request_body.top_p,  # Nucleus sampling
                top_k=50,  # Top-k sampling
                repetition_penalty=1.2,  # Penalize repetition
                no_repeat_ngram_size=3,  # Prevent repeating 3-grams
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        # ⭐ KEY FIX: Decode ONLY the new tokens (skip the input)
        generated_ids = outputs[0][input_length:]
        generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
        print(f"📊 Generated: {len(generated_ids)} tokens")
        print(f"✅ Response: {generated_text[:100]}...")
        print(f"{'='*60}\n")

        return {
            "generated_text": generated_text,
            "prompt": prompt
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": "Llama-3.1-8B-finetuned",
        "gpu": torch.cuda.is_available(),
        "device": str(model.device) if 'model' in globals() else "not loaded"
    }

@app.get("/")
async def root():
    return {
        "message": "Colab LLM API is running!",
        "endpoints": {
            "/generate": "POST - Generate text",
            "/health": "GET - Health check"
        }
    }

print("✅ FastAPI app created!")

# To run this in Colab, add at the end:
# public_url = ngrok.connect(8000)
# print(f"🌐 Public URL: {public_url}")
# uvicorn.run(app, host="0.0.0.0", port=8000)
