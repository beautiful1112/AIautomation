import asyncio
import fastapi_poe as fp
import json

async def get_responses(api_key, messages):
    full_response = ""
    async for partial in fp.get_bot_response(messages=messages, bot_name="GPT-3.5-Turbo", api_key=api_key):
        if partial.text:
            try:
                text_content = json.loads(partial.text)['text']
                full_response += text_content
                print(text_content, end='', flush=True)
            except json.JSONDecodeError:
                print(partial.text, end='', flush=True)
    print()  # 打印一个换行
    return full_response

api_key = "use your API-key"
message = fp.ProtocolMessage(role="user", content="Hi,hello~")

asyncio.run(get_responses(api_key, [message]))a