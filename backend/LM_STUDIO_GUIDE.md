# LM Studio Setup Guide for MOODZ

To use a local LLM with MOODZ via LM Studio, follow these steps:

1.  **Download and Install LM Studio**: [lmstudio.ai](https://lmstudio.ai/)
2.  **Download a Model**: Search for a model like `Meta-Llama-3-8B-Instruct-GGUF` or `Mistral-7B-Instruct-v0.2-GGUF`.
3.  **Load the Model**: Go to the **AI Chat** tab or **Local Server** tab and load the model.
4.  **Start the Local Server**:
    - Click the **Local Server** tab (icon looks like a double arrow/server).
    - Set the port to `1234` (default).
    - Ensure **CORS** is enabled (it usually is by default for local requests).
    - Click **Start Server**.
5.  **Configure MOODZ**:
    - Your `.env` file has been updated to point to `http://localhost:1234/v1`.
    - `USE_CUSTOM_MODEL` is set to `True`.
    - `CUSTOM_MODEL_TYPE` is set to `openai`.

Once the server is running in LM Studio, the MOODZ backend will automatically routes requests to your local model.
