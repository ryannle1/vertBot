import requests
import os
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to get host from environment, fallback to localhost
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# If running in Docker and OLLAMA_HOST is not set, use the service name
if OLLAMA_HOST == "http://localhost:11434" and os.getenv("DOCKER_ENV"):
    OLLAMA_HOST = "http://ollama:11434"

# Using Mistral 7B Instruct for financial analysis
MODEL_NAME = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")

def query_deepseek(prompt, system_prompt=None, max_retries=3):
    url = f"{OLLAMA_HOST}/api/generate"
    headers = {"Content-Type": "application/json"}
    
    # Format prompt for Mistral
    formatted_prompt = f"""<s>[INST] You are a financial analysis expert. Analyze the following information and provide insights:

{prompt}
[/INST]</s>"""
    
    data = {
        "model": MODEL_NAME,
        "prompt": formatted_prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40
        }
    }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to Ollama at {OLLAMA_HOST} (attempt {attempt + 1}/{max_retries})")
            logger.info(f"Using model: {MODEL_NAME}")
            logger.info(f"Request URL: {url}")
            
            # Increase timeout for larger responses
            response = requests.post(url, json=data, headers=headers, timeout=60)
            
            # Log the response status and content for debugging
            logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code == 404:
                logger.error(f"404 error - Endpoint not found. Please check if Ollama is running and the API endpoint is correct.")
                raise ConnectionError("Ollama API endpoint not found. Please check if Ollama is running and the API endpoint is correct.")
                
            response.raise_for_status()
            output = response.json()
            return output.get("response") or output.get("output")
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Request to Ollama timed out (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)  # Wait before retrying
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Ollama at {OLLAMA_HOST}. Make sure the container is running and accessible.")
            logger.error(f"Connection error: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)  # Wait before retrying
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to Ollama: {str(e)}")
            logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)  # Wait before retrying
