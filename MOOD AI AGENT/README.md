---
title: MOODZ AI Agent
emoji: 🎭
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# MOODZ AI Agent

AI-powered mood analysis and mental wellness companion.

## Features
- 🎭 Mood tracking and analysis
- 💬 Conversational AI support
- 📊 Personalized insights
- 🔒 Privacy-focused design

## Configuration

This Space uses Docker and requires the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key
- `PINECONE_API_KEY`: Your Pinecone API key
- `PINECONE_ENVIRONMENT`: Your Pinecone environment
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

Set these in the Space settings under "Repository secrets".
