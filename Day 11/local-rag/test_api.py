from openai import OpenAI
import config
import os
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY"))

response = client.chat.completions.create(
    model=os.getenv("LLM_MODEL"),
    messages=[{"role": "user", "content": "Say hello in one sentence."}],
    temperature=0.3,
    reasoning_effort="none",
    max_completion_tokens=100,
)
print(response.choices[0].message.content)
print(response.choices[0].finish_reason)

print(os.getenv("LLM_MODEL"))
