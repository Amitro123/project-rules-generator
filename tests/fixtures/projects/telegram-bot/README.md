# Telegram Customer Support Agent

A Telegram bot that handles customer queries using LangGraph for workflow
orchestration and ChromaDB for RAG.

## Stack

- Python 3.11
- LangGraph (workflow orchestration — NOT LangChain alone)
- python-telegram-bot v20 (async handlers)
- ChromaDB (vector store for the knowledge base)
- OpenAI / GPT for responses
- AWS Lambda for deployment

## Tests

This project uses pytest with `pytest-asyncio`. There is NO JavaScript, NO Jest,
NO React. Bug4 in PRG's `ListOfBugs/` documented `jest` falsely appearing in
the detected tech_stack here — the leak came from the global learned-skill
library having entries tagged `jest`.
