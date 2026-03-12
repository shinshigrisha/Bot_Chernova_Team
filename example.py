# from openai import OpenAI  # Commented out because the 'openai' module is not installed or missing.
client = OpenAI()

response = client.responses.create(
    model="gpt-5.4",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)