# Fix Repetitive Text Generation in Colab Server

## Problem Identified

Your model is generating repetitive text:
```
I'm feeling anxious because I'm about to ask my boss for a raise.
I'm feeling anxious because I'm about to ask my boss for a raise.
I'm feeling anxious because I'm about to ask my boss for a raise.
...
```

This is a **Colab server issue**, not a backend integration issue. The API is working correctly!

## Root Causes

1. ❌ Missing `repetition_penalty` parameter
2. ❌ No proper chat template/formatting
3. ❌ Incorrect generation parameters
4. ❌ Model might need instruction formatting

## Solution: Update Your Colab Server Code

### Option 1: Quick Fix - Add Repetition Penalty

In your Colab server's `/generate` endpoint, update the `model.generate()` call:

```python
@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 2048)
        
        # Tokenize input
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        # Generate with proper parameters to prevent repetition
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,  # Enable sampling
                top_p=0.9,  # Nucleus sampling
                top_k=50,  # Top-k sampling
                repetition_penalty=1.2,  # ⭐ KEY FIX - Penalize repetition
                no_repeat_ngram_size=3,  # ⭐ Prevent repeating 3-grams
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # Decode response
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove the prompt from response (model includes it)
        if full_text.startswith(prompt):
            generated_text = full_text[len(prompt):].strip()
        else:
            generated_text = full_text
        
        return jsonify({
            "generated_text": generated_text,
            "prompt": prompt
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### Option 2: Better Fix - Use Chat Template (Recommended)

If you're using a chat model like Llama-3.1-8B-Instruct, use the proper chat template:

```python
@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        user_message = data.get('prompt', '')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 2048)
        
        # Format as a chat conversation
        messages = [
            {
                "role": "system",
                "content": "You are MOODZ, an empathetic AI mood companion and mental wellness assistant. Provide warm, supportive, and helpful responses."
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
        
        # Apply chat template
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        # Generate with proper parameters
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.2,  # Prevent repetition
                no_repeat_ngram_size=3,  # Prevent repeating phrases
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # Decode only the new tokens (not the prompt)
        generated_ids = outputs[0][inputs['input_ids'].shape[1]:]
        generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        return jsonify({
            "generated_text": generated_text.strip(),
            "prompt": user_message
        })
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
```

### Option 3: Use Text Generation Pipeline (Easiest)

```python
from transformers import pipeline

# Load model as pipeline
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    device=0 if torch.cuda.is_available() else -1
)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 512)
        
        # Generate using pipeline
        result = generator(
            prompt,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.2,
            no_repeat_ngram_size=3,
            return_full_text=False  # Only return generated text
        )
        
        generated_text = result[0]['generated_text']
        
        return jsonify({
            "generated_text": generated_text,
            "prompt": prompt
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## Key Parameters Explained

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `repetition_penalty` | 1.2 | Penalize repeated tokens (1.0 = no penalty, higher = more penalty) |
| `no_repeat_ngram_size` | 3 | Prevent repeating sequences of 3 words |
| `temperature` | 0.7 | Randomness (0 = deterministic, 1 = creative) |
| `top_p` | 0.9 | Nucleus sampling - only sample from top 90% probability mass |
| `top_k` | 50 | Only consider top 50 tokens at each step |
| `do_sample` | True | Enable random sampling (required for temperature > 0) |

## Testing After Fix

1. **Update your Colab server** with one of the solutions above
2. **Restart the Flask server** in Colab
3. **Run the test again**:
   ```bash
   python test_api_direct.py
   ```

You should now see varied, non-repetitive responses!

## Expected Good Response

After fixing, you should see something like:
```json
{
    "generated_text": "I understand that you're feeling anxious today. Anxiety can be challenging, but there are several strategies that might help. Would you like to talk about what's causing your anxiety? Sometimes sharing your feelings can help. I can also suggest some calming techniques like deep breathing exercises or mindfulness practices.",
    "prompt": "Hello! I'm feeling a bit anxious today. Can you help me?"
}
```

## Additional Tips

### 1. For Llama Models
If using Llama-3.1-8B-Instruct, always use the chat template:
```python
# Check if model has chat template
if hasattr(tokenizer, 'chat_template') and tokenizer.chat_template:
    print("✅ Model supports chat template")
else:
    print("⚠️  Model doesn't have chat template, using plain text")
```

### 2. Adjust Repetition Penalty
- Too low (< 1.1): May still repeat
- Good range: 1.1 - 1.3
- Too high (> 1.5): May produce incoherent text

### 3. Monitor Generation Quality
Add logging to see what's being generated:
```python
print(f"Input length: {len(inputs['input_ids'][0])} tokens")
print(f"Output length: {len(outputs[0])} tokens")
print(f"Generated: {generated_text[:100]}...")
```

### 4. Handle Long Contexts
If the prompt is very long, the model might struggle:
```python
# Limit input length
max_input_length = 2048
if len(inputs['input_ids'][0]) > max_input_length:
    inputs['input_ids'] = inputs['input_ids'][:, -max_input_length:]
    inputs['attention_mask'] = inputs['attention_mask'][:, -max_input_length:]
```

## Troubleshooting

### Still getting repetition?
- Increase `repetition_penalty` to 1.5
- Decrease `temperature` to 0.5
- Add `no_repeat_ngram_size=4`

### Responses are incoherent?
- Decrease `repetition_penalty` to 1.1
- Increase `temperature` to 0.8
- Increase `top_p` to 0.95

### Model is slow?
- Reduce `max_tokens` to 256
- Use `torch.float16` instead of `float32`
- Enable GPU in Colab (Runtime → Change runtime type → GPU)

### Out of memory?
- Use smaller `max_tokens`
- Use model quantization (int8 or int4)
- Clear cache: `torch.cuda.empty_cache()`

## Complete Working Example

Here's a complete, tested endpoint:

```python
@app.route('/generate', methods=['POST'])
def generate():
    """Generate text with proper anti-repetition measures."""
    try:
        # Parse request
        data = request.json
        user_message = data.get('prompt', '')
        temperature = max(0.1, min(data.get('temperature', 0.7), 1.0))  # Clamp
        max_tokens = min(data.get('max_tokens', 512), 2048)  # Limit
        
        print(f"\n📝 Generating for: {user_message[:50]}...")
        
        # Tokenize
        inputs = tokenizer(user_message, return_tensors="pt").to(model.device)
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.2,
                no_repeat_ngram_size=3,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # Decode
        full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove prompt
        if full_text.startswith(user_message):
            generated_text = full_text[len(user_message):].strip()
        else:
            generated_text = full_text.strip()
        
        print(f"✅ Generated {len(generated_text)} characters")
        
        return jsonify({
            "generated_text": generated_text,
            "prompt": user_message,
            "tokens_generated": len(outputs[0]) - len(inputs['input_ids'][0])
        })
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
```

## Next Steps

1. ✅ Update your Colab server with the fixes above
2. ✅ Restart the server
3. ✅ Test with `python test_api_direct.py`
4. ✅ Once working, test the full integration with your MOODZ backend

The backend integration code is already correct and will work perfectly once your Colab server returns proper responses!
