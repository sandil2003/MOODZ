"""
Sample Flask Server for Google Colab
=====================================

This is a reference implementation for hosting your custom model
on Google Colab and exposing it via ngrok.

INSTRUCTIONS:
1. Upload this file to Google Colab or copy the code into a notebook
2. Install required packages
3. Update the model loading section with your model
4. Run the server
5. Copy the ngrok URL to your .env file

"""

# ============================================================================
# STEP 1: Install Required Packages
# ============================================================================
# Run this in a Colab cell:
"""
!pip install flask pyngrok transformers torch accelerate
"""

# ============================================================================
# STEP 2: Import Libraries
# ============================================================================
from flask import Flask, request, jsonify
from pyngrok import ngrok
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os

# ============================================================================
# STEP 3: Configure ngrok (Optional - for custom domain)
# ============================================================================
# If you have an ngrok auth token, set it here:
# ngrok.set_auth_token("YOUR_NGROK_AUTH_TOKEN")

# ============================================================================
# STEP 4: Initialize Flask App
# ============================================================================
app = Flask(__name__)

# ============================================================================
# STEP 5: Load Your Model
# ============================================================================
print("Loading model...")

# OPTION A: Load from Hugging Face
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"  # Replace with your model

# OPTION B: Load from local path (if you uploaded a model)
# MODEL_NAME = "/content/my-custom-model"

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,  # Use float16 for faster inference
        device_map="auto",  # Automatically use GPU if available
        low_cpu_mem_usage=True
    )
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    raise

# ============================================================================
# STEP 6: Define API Endpoints
# ============================================================================

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint."""
    return jsonify({
        "status": "online",
        "model": MODEL_NAME,
        "message": "Custom model server is running!"
    })


@app.route('/generate', methods=['POST'])
def generate():
    """
    Main generation endpoint.
    
    Expected JSON payload:
    {
        "prompt": "Your prompt here",
        "temperature": 0.7,
        "max_tokens": 2048,
        "stop": ["optional", "stop", "sequences"]
    }
    
    Returns:
    {
        "generated_text": "Model response here"
    }
    """
    try:
        # Parse request
        data = request.json
        
        if not data or 'prompt' not in data:
            return jsonify({
                "error": "Missing 'prompt' in request body"
            }), 400
        
        prompt = data.get('prompt', '')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 2048)
        stop_sequences = data.get('stop', None)
        
        print(f"\n📝 Received prompt: {prompt[:100]}...")
        print(f"⚙️  Temperature: {temperature}, Max tokens: {max_tokens}")
        
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        # Generate response
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # Decode response
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove the prompt from the response (model often includes it)
        if generated_text.startswith(prompt):
            generated_text = generated_text[len(prompt):].strip()
        
        print(f"✅ Generated response: {generated_text[:100]}...")
        
        return jsonify({
            "generated_text": generated_text,
            "model": MODEL_NAME,
            "tokens_generated": len(outputs[0]) - len(inputs['input_ids'][0])
        })
    
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        return jsonify({
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Detailed health check."""
    return jsonify({
        "status": "healthy",
        "model": MODEL_NAME,
        "device": str(model.device),
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    })


# ============================================================================
# STEP 7: Start Server with ngrok
# ============================================================================

def start_server(port=5000):
    """Start Flask server with ngrok tunnel."""
    
    print("\n" + "="*60)
    print("🚀 Starting Custom Model Server")
    print("="*60)
    
    # Start ngrok tunnel
    try:
        public_url = ngrok.connect(port)
        print(f"\n✅ ngrok tunnel established!")
        print(f"📡 Public URL: {public_url}")
        print(f"\n⚠️  IMPORTANT: Copy this URL to your .env file:")
        print(f"   CUSTOM_MODEL_URL={public_url}")
        print("\n" + "="*60)
    except Exception as e:
        print(f"❌ Error starting ngrok: {e}")
        print("Continuing without ngrok tunnel...")
    
    # Start Flask app
    print(f"\n🌐 Starting Flask server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)


# ============================================================================
# STEP 8: Run the Server
# ============================================================================

if __name__ == '__main__':
    start_server(port=5000)


# ============================================================================
# TESTING THE SERVER
# ============================================================================
"""
After the server starts, test it with curl:

# Health check
curl https://your-ngrok-url.ngrok-free.dev/health

# Generate text
curl -X POST https://your-ngrok-url.ngrok-free.dev/generate \
  -H "Content-Type: application/json" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{
    "prompt": "Hello! I am feeling anxious today.",
    "temperature": 0.7,
    "max_tokens": 512
  }'
"""

# ============================================================================
# NOTES FOR GOOGLE COLAB
# ============================================================================
"""
1. GPU Runtime:
   - Go to Runtime > Change runtime type > Select GPU
   - This will significantly speed up inference

2. Keep Colab Active:
   - Colab disconnects after ~90 minutes of inactivity
   - Use this JavaScript in browser console to keep it active:
   
   function ClickConnect(){
     console.log("Clicking connect button"); 
     document.querySelector("colab-connect-button").click()
   }
   setInterval(ClickConnect, 60000)

3. ngrok Free Tier Limitations:
   - URLs expire when the session ends
   - Limited to 40 connections/minute
   - Consider upgrading for production use

4. Model Loading:
   - First run will download the model (can take several minutes)
   - Subsequent runs will use cached model
   - Make sure you have enough disk space

5. Memory Management:
   - Use float16 for large models
   - Consider model quantization (int8, int4) for even faster inference
   - Monitor GPU memory usage

6. Security:
   - Add authentication if exposing publicly
   - Implement rate limiting
   - Validate all inputs
"""
