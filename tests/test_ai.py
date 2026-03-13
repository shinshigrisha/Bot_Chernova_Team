from openai import OpenAI

client = OpenAI(
    api_key="sk-vl2S17w8dQ06ihyZc1sRO4nFMmbKESw3j7TIv9yZyMY7bl8F",
    base_url="https://api.aiguoguo199.com/v1"
)

response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "user", "content": "Напиши короткое приветствие"}
    ]
)

print(response.choices[0].message.content)