from openai import OpenAI

client = OpenAI(api_key="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")

name = "妮赖"
bio = "A passionate software developer from Shanghai."
dob = "1995-08-15"

prompt = (
    f"Given the following information:\n"
    f"Name: {name}\n"
    f"Bio: {bio}\n"
    f"Date of Birth: {dob}\n"
    "Predict the most likely gender and age (in years). "
    "Respond in JSON format: {\"gender\": \"male/female/other\", \"age\": eg; 20 - 30}"
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that predicts gender and age from name, bio, and date of birth."},
        {"role": "user", "content": prompt}
    ]
)

result = response.choices[0].message.content.strip()
print(result)
