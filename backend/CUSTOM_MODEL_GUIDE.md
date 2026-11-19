# Custom Model Integration Guide

This guide explains how to use your custom model hosted on Google Colab (via ngrok) with the MOODZ AI Agent instead of OpenAI.

## Overview

The MOODZ AI Agent now supports using a custom model hosted externally via ngrok. This allows you to:
- Use your own fine-tuned models
- Reduce API costs
- Have full control over the inference process
- Test custom models before deploying to production

## Architecture

```
┌─────────────────┐
│  MOODZ Frontend │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI Backend│
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  MoodAgentChain │─────▶│  CustomModelLLM  │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
                         ┌────────────────┐
                         │  ngrok Tunnel  │
                         └────────┬───────┘
                                  │
                                  ▼
                         ┌────────────────┐
                         │ Google Colab   │
                         │ Custom Model   │
                         └────────────────┘
```

## Setup Instructions

### 1. Configure Environment Variables

Edit your `.env` file and set the following variables:

```bash
# Custom Model Configuration
USE_CUSTOM_MODEL=True
CUSTOM_MODEL_URL=https://unharping-unhumidified-chara.ngrok-free.dev
CUSTOM_MODEL_TEMPERATURE=0.7
CUSTOM_MODEL_MAX_TOKENS=2048
CUSTOM_MODEL_TIMEOUT=60
```

**Configuration Options:**
- `USE_CUSTOM_MODEL`: Set to `True` to use custom model, `False` to use OpenAI
- `CUSTOM_MODEL_URL`: Your ngrok URL (without trailing slash)
- `CUSTOM_MODEL_TEMPERATURE`: Controls randomness (0.0 = deterministic, 1.0 = creative)
- `CUSTOM_MODEL_MAX_TOKENS`: Maximum tokens to generate
- `CUSTOM_MODEL_TIMEOUT`: Request timeout in seconds

### 2. API Endpoint Requirements

Your custom model server must expose a `/generate` endpoint that:

**Accepts POST requests with JSON payload:**
```json
{
  "prompt": "User's message here",
  "temperature": 0.7,
  "max_tokens": 2048,
  "stop": ["optional", "stop", "sequences"]
}
```

**Returns JSON response in one of these formats:**
```json
{
  "generated_text": "Model's response here"
}
```
or
```json
{
  "text": "Model's response here"
}
```
or
```json
{
  "response": "Model's response here"
}
```

### 3. Google Colab Server Example

Here's a basic Flask server you can run in Google Colab:

```python
from flask import Flask, request, jsonify
from pyngrok import ngrok
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

app = Flask(__name__)

# Load your model
model_name = "your-model-name"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 2048)
        
        # Tokenize and generate
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True
        )
        
        # Decode response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return jsonify({
            "generated_text": response
        })
    
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Start ngrok tunnel
    public_url = ngrok.connect(5000)
    print(f"Public URL: {public_url}")
    
    # Run Flask app
    app.run(port=5000)
```

## Testing

### Test the Custom Model Connection

Run the test script to verify your custom model is working:

```bash
python test_custom_model.py
```

Expected output:
```
============================================================
Testing Custom Model Integration
============================================================

Configuration:
  USE_CUSTOM_MODEL: True
  CUSTOM_MODEL_URL: https://unharping-unhumidified-chara.ngrok-free.dev
  Temperature: 0.7
  Max Tokens: 2048
  Timeout: 60s

📡 Connecting to custom model at: https://unharping-unhumidified-chara.ngrok-free.dev

📝 Test Prompt:
  Hello! I'm feeling a bit anxious today. Can you help me?

⏳ Generating response...

✅ Response received:
  [Your model's response here]

============================================================
✅ Custom model test completed successfully!
============================================================
```

### Test with Full Application

1. Restart your FastAPI server:
   ```bash
   python main.py
   ```

2. Look for the log message:
   ```
   Using custom model from: https://unharping-unhumidified-chara.ngrok-free.dev
   ```

3. Test via the frontend or API:
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test-user",
       "session_id": "test-session",
       "message": "Hello, how are you?"
     }'
   ```

## Switching Between Models

### Use Custom Model
Set in `.env`:
```bash
USE_CUSTOM_MODEL=True
```

### Use OpenAI
Set in `.env`:
```bash
USE_CUSTOM_MODEL=False
```

No code changes required! Just restart the server.

## Troubleshooting

### Error: Request timed out
- **Solution**: Increase `CUSTOM_MODEL_TIMEOUT` in `.env`
- Check if your Colab instance is still running
- Verify ngrok tunnel is active

### Error: HTTP 404 - Not Found
- **Solution**: Verify your server has a `/generate` endpoint
- Check the `CUSTOM_MODEL_URL` is correct

### Error: Connection refused
- **Solution**: Ensure your Colab server is running
- Verify the ngrok URL is still active (ngrok URLs expire)
- Check firewall settings

### ngrok browser warning
- The custom model automatically adds `ngrok-skip-browser-warning` header
- If you still see warnings, update your ngrok configuration

### Model responses are slow
- **Solutions**:
  - Use a smaller model
  - Reduce `CUSTOM_MODEL_MAX_TOKENS`
  - Use GPU acceleration in Colab
  - Consider using a paid ngrok plan for better bandwidth

## API Response Format

The `CustomModelLLM` class automatically handles multiple response formats:

1. `{"generated_text": "..."}`
2. `{"text": "..."}`
3. `{"response": "..."}`

If your API uses a different format, modify `custom_model.py`:

```python
# In _call and _acall methods, update this section:
if isinstance(result, dict):
    generated_text = (
        result.get("generated_text") or 
        result.get("text") or 
        result.get("response") or
        result.get("your_custom_key", "")  # Add your key here
    )
```

## Performance Tips

1. **Use GPU in Colab**: Enable GPU runtime for faster inference
2. **Batch Processing**: If handling multiple requests, consider batching
3. **Model Quantization**: Use quantized models (int8, int4) for faster inference
4. **Caching**: Implement response caching for common queries
5. **Keep Colab Active**: Use auto-refresh scripts to prevent disconnection

## Security Considerations

1. **Authentication**: Add API key authentication to your Colab server
2. **Rate Limiting**: Implement rate limiting to prevent abuse
3. **Input Validation**: Validate and sanitize all inputs
4. **HTTPS Only**: Always use HTTPS (ngrok provides this by default)
5. **Secrets Management**: Never commit ngrok URLs or API keys to git

## Files Modified

- `app/services/custom_model.py` - New custom model LLM wrapper
- `app/services/mood_chain.py` - Updated to support custom model
- `config.py` - Added custom model configuration
- `.env` - Added custom model environment variables
- `test_custom_model.py` - Test script for custom model

## Support

If you encounter issues:
1. Check the test script output
2. Verify your Colab server logs
3. Check FastAPI server logs
4. Ensure all environment variables are set correctly

## Future Enhancements

Potential improvements:
- [ ] Support for streaming responses
- [ ] Multiple model endpoints (A/B testing)
- [ ] Automatic failover to OpenAI if custom model fails
- [ ] Model performance monitoring
- [ ] Response caching layer
