"""
LLM configuration using a local Ollama instance running qwen-20b.
"""



from langchain_ollama import ChatOllama


llm = ChatOllama(
    model="gpt-oss:20b",
    temperature=0,
    base_url="http://192.168.229.1:11434",
    # other params...
)


