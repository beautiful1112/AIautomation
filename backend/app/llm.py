"""
LLM configuration using a local Ollama instance running qwen-20b.
"""



from langchain_ollama import ChatOllama


llm = ChatOllama(
    model="gpt-oss:20b",
    temperature=0,
    # other params...
)


