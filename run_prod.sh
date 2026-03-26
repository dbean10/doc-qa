#!/bin/bash
export ANTHROPIC_API_KEY=$(gcloud secrets versions access latest --secret=ANTHROPIC_API_KEY)
export OPENAI_API_KEY=$(gcloud secrets versions access latest --secret=OPENAI_API_KEY)
export ENVIRONMENT=production
uv run python -m "${1:-lab4.chatbot}"
