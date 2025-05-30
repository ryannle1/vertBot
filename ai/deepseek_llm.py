import requests
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-r1")

def query_deepseek(prompt, system_prompt=None):
    url = f"{OLLAMA_HOST}/api/generate"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    if system_prompt:
        data["system"] = system_prompt
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    output = response.json()
    return output.get("response") or output.get("output")
