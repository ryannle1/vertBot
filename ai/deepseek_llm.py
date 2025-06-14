import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to get host from environment, fallback to localhost
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# If running in Docker and OLLAMA_HOST is not set, use the service name
if OLLAMA_HOST == "http://localhost:11434" and os.getenv("DOCKER_ENV"):
    OLLAMA_HOST = "http://ollama:11434"

MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-coder:6.7b-instruct")

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
    
    try:
        logger.info(f"Attempting to connect to Ollama at {OLLAMA_HOST}")
        logger.info(f"Using model: {MODEL_NAME}")
        logger.info(f"Request URL: {url}")
        logger.info(f"Request data: {data}")
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        # Log the response status and content for debugging
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        
        if response.status_code == 404:
            logger.error(f"404 error - Endpoint not found. Please check if Ollama is running and the API endpoint is correct.")
            logger.error(f"Full response: {response.text}")
            raise ConnectionError("Ollama API endpoint not found. Please check if Ollama is running and the API endpoint is correct.")
            
        response.raise_for_status()
        output = response.json()
        return output.get("response") or output.get("output")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Failed to connect to Ollama at {OLLAMA_HOST}. Make sure the container is running and accessible.")
        logger.error(f"Connection error: {str(e)}")
        raise
    except requests.exceptions.Timeout as e:
        logger.error(f"Request to Ollama timed out after 30 seconds")
        logger.error(f"Timeout error: {str(e)}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making request to Ollama: {str(e)}")
        logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
        raise
