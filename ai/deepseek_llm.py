import aiohttp
import os
import logging
import asyncio
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
MODEL_NAME = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")

async def query_deepseek(prompt, system_prompt=None, max_retries=3):
    url = f"{OLLAMA_HOST}/api/generate"
    headers = {"Content-Type": "application/json"}
    
    # Format prompt for DeepSeek R1
    formatted_prompt = f"You are a financial analysis expert. Analyze the following information and provide insights:\n\n{prompt}"
    
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
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to Ollama at {OLLAMA_HOST} (attempt {attempt + 1}/{max_retries})")
                logger.info(f"Using model: {MODEL_NAME}")
                logger.info(f"Request URL: {url}")
                
                async with session.post(url, json=data, headers=headers, timeout=60) as response:
                    # Log the response status for debugging
                    logger.info(f"Response status code: {response.status}")
                    
                    if response.status == 404:
                        logger.error(f"404 error - Endpoint not found. Please check if Ollama is running and the API endpoint is correct.")
                        raise ConnectionError("Ollama API endpoint not found. Please check if Ollama is running and the API endpoint is correct.")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error response: {error_text}")
                        raise ConnectionError(f"Ollama API returned status {response.status}")
                    
                    output = await response.json()
                    return output.get("response") or output.get("output")
                    
            except asyncio.TimeoutError as e:
                logger.error(f"Request to Ollama timed out (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)  # Wait before retrying
                
            except aiohttp.ClientError as e:
                logger.error(f"Failed to connect to Ollama at {OLLAMA_HOST}. Make sure the container is running and accessible.")
                logger.error(f"Connection error: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)  # Wait before retrying
                
            except Exception as e:
                logger.error(f"Error making request to Ollama: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)  # Wait before retrying
