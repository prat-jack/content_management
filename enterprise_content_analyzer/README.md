# Enterprise Content Analysis Platform

This platform analyzes business documents using AI.

## Setup

1.  **Create and activate virtual environment:**
    ```bash
    uv venv
    source .venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    uv pip install -r requirements.txt
    ```
3.  **Configure API Key:**
    - Create a `.env` file from the `.env.example`.
    - Add your OpenAI API key to the `.env` file.
4.  **Run the application:**
    ```bash
    streamlit run app.py
    ```