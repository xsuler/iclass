import os
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()    

def analyze_image(image_path, prompt="What's in this image?"):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://openrouter.ai/api/v1")
    
    # Prepare image content
    if image_path.startswith("http"):
        image_content = {"url": image_path}
    else:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            image_content = {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
    
    # Create message payload
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that analyzes and describes images in detail."
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": image_content
                }
            ]
        }
    ]
    
    # Get response from OpenAI
    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=messages,
        response_format={"type": "json_object"}
    )
    
    return response.choices[0].message.content
