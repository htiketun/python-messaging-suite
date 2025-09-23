from openai import OpenAI

client = OpenAI(api_key="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")

name = "妮赖"

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that accurately classifies names by likely gender. "},
        {"role": "user", "content": f"What is the gender of the name '{name}'?"},
        {"role": "assistant", "content": "Respond with only one word: 'male', 'female'likely to be."}
    ]
)

gender = response.choices[0].message.content.strip().lower()
print(gender)
