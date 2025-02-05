import fastapi_poe as fp
import json

class POEClient:
    def __init__(self, api_key, bot_name):
        self.api_key = api_key
        self.bot_name = bot_name

    async def analyze_log(self, log_data):
        message = fp.ProtocolMessage(
            role="user",
            content=f"Analyze this Cisco device log and explain what happened: {json.dumps(log_data)}"
        )
        return await self._get_response([message])

    async def get_repair_suggestion(self, analysis):
        message = fp.ProtocolMessage(
            role="user",
            content=f"Based on this analysis, provide specific Cisco IOS commands to fix any issues (if needed): {analysis}"
        )
        return await self._get_response([message])

    async def _get_response(self, messages):
        full_response = ""
        async for partial in fp.get_bot_response(
            messages=messages,
            bot_name=self.bot_name,
            api_key=self.api_key
        ):
            if partial.text:
                try:
                    text_content = json.loads(partial.text)['text']
                    full_response += text_content
                except json.JSONDecodeError:
                    full_response += partial.text
        return full_response