import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key = os.environ["GEMINI_API_KEY"])

original_text = "Agentic AI refers to AI systems that can take autonomous, goal-directed actions rather than just generating passive responses. These systems can perceive context, reason about what to do next, break tasks into steps, use tools or external systems, coordinate with other agents, and adapt based on feedback—essentially behaving more like proactive problem-solvers than traditional chatbots."
prompt1 = f"Summarise the following text in one sentence: {original_text}"

response1 = client.models.generate_content(
    model = "gemini-2.5-flash", 
    contents = prompt1
) 

summary = response1.text.strip()
print(f"summary: {summary}")

prompt2 = f"Tranlate the following summary into French, only return the translation, no other text: {summary}"

response2 = client.models.generate_content(
    model = "gemini-2.5-flash", 
    contents = prompt2
) 

translation = response2.text.strip()
print(f"Translation: {translation}")
