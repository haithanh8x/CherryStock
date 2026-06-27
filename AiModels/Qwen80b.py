from openrouter import OpenRouter
from lstPara import OPENROUTER_API_KEY

with OpenRouter(
  api_key=OPENROUTER_API_KEY,
) as client:
  response = client.chat.send(
    model="qwen/qwen3-next-80b-a3b-instruct",
    messages=[
      {
        "role": "user",
        "content": "What is the meaning of life?"
      }
    ]
  )

  print(response.choices[0].message.content)