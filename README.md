# OpenRouter Python Template

This project provides a minimal Python example for calling OpenRouter's OpenAI-compatible chat completion API.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example environment file and add your API key:
   ```bash
   cp .env.example .env
   ```
4. Run the script:
   ```bash
   python main.py
   ```

## Notes

- Set your OpenRouter API key in `.env`.
- You can change the model and prompt in `.env`.
