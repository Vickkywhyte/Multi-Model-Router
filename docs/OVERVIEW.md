
Multi-Model Router
An AI Gateway for Cost-Aware Language Model Routing


Project Overview & Technical Explanation
September 2026
github.com/Vickkywhyte/Multi-Model-Router

Contents


1. What This Project Is
2. The Problem It Solves
3. How It Works (The Big Picture)
4. The Three AI Models
5. The Complexity Classifier
6. Technology Used
7. What the System Tracks
8. The Dashboard
9. How to Run It
10. Project Structure
11. Quality & Testing
12. What Could Come Next
13. Summary

1. What This Project Is


The Multi-Model Router is a software service that acts as an intelligent middleman between you and Google's AI language models (called Gemini). Instead of you having to decide which AI model to use for each question, the router analyses your question automatically, figures out how complex it is, and sends it to the most cost-effective model that can handle it well.
Think of it like a postal service that looks at each package and decides whether it needs express delivery or standard post. A simple letter does not need a courier; a fragile antique does. The router does the same thing for AI requests — it matches the difficulty of the question to the right level of AI, saving money without sacrificing the quality of answers.
2. The Problem It Solves


Companies using AI language models face a surprisingly common dilemma. The most powerful (and expensive) models cost roughly 10 to 30 times more per request than smaller, cheaper ones. Yet for straightforward questions like "What is the capital of France?" the cheap model and the expensive model give identical answers.
Without a router, teams typically do one of two things:
Always use the most powerful model — which wastes enormous amounts of money on questions that do not need it.
Always use the cheapest model — which produces poor answers for complex tasks like writing code, analysing data, or reasoning through multi-step problems.
The Multi-Model Router solves this by making the decision automatically for every single request, then logging the cost and quality of each answer so you can see the savings over time.
3. How It Works (The Big Picture)


When someone sends a question to the router, the following steps happen in order, all within a few seconds:
Step 1 — Receive: The question arrives at the service through a web address (called an API endpoint).
Step 2 — Classify: A built-in classifier examines the question and assigns it a complexity label: simple, medium, or complex.
Step 3 — Route: Based on that label, the router selects the cheapest Google Gemini model capable of answering it well.
Step 4 — Call the AI: The question is sent to the chosen Gemini model, which generates an answer.
Step 5 — Log everything: The system records which model was used, how many tokens (word-fragments) were consumed, how long the response took, and the cost in US dollars.
Step 6 — Respond: The answer is returned to the user along with metadata showing the model used, the cost, and the latency.

4. The Three AI Models


The router uses three tiers of Google Gemini models. Each tier trades off cost against capability:
Tier
Model Name
Best For
Relative Cost
Simple
Gemini 3.5 Flash Lite
Quick facts, definitions, short translations
Cheapest (≈$0.30 per million input tokens)
Medium
Gemini 3.5 Flash
Summaries, moderate reasoning, conversational AI
Mid-range (≈$1.50 per million input tokens)
Complex
Gemini 2.5 Pro
Code generation, multi-step analysis, nuanced reasoning
Most capable (≈$1.25 input / $10.00 output per million tokens)


By routing simple questions to Flash Lite instead of the Pro model, the system can reduce costs by 50% or more on average, while keeping answer quality high for the questions that genuinely need the bigger model.
5. The Complexity Classifier


The classifier is the brain of the routing decision. It is a rule-based system (no AI call needed for classification itself) that examines several properties of each incoming question:
Prompt length — longer, more detailed prompts tend to be more complex.
Keyword heuristics — words like "analyse", "compare", "debug", or "implement" signal higher complexity.
Code fences — if the prompt contains code blocks, it likely needs a capable coding model.
Question count — multiple questions in a single prompt increase complexity.
Based on these signals, the classifier assigns one of three labels: simple, medium, or complex. This classification happens instantly and costs nothing — no AI tokens are used for the classification step itself.

6. Technology Used


This section describes the tools and technologies that make up the system. Each was chosen for a specific reason.
Programming Language & Framework
Python 3.11 is the programming language. Python is the dominant language in AI and data applications because of its rich ecosystem of libraries.
FastAPI is the web framework that receives and responds to requests. It is modern, fast, and automatically generates interactive documentation for the API.
Database & Storage
PostgreSQL 16 (Postgres) is the main database. Every request, its cost, latency, model used, and quality score is stored here. Postgres is an industry-standard, open-source relational database known for reliability.
Redis 7 is an in-memory data store provisioned for future use — it will be used for caching repeated questions so the system does not call the AI again for identical prompts.
SQLAlchemy 2.0 is the library that lets Python talk to Postgres. It is used in "async" mode, meaning the application never sits idle waiting for the database — it can handle many requests simultaneously.
Alembic manages database migrations — it tracks changes to the database structure over time so they can be applied consistently across environments.
AI Provider
Google Gemini is the AI provider, accessed through the google-genai Python SDK. The system is designed with an abstract "provider" layer, meaning a different AI provider (like OpenAI or Anthropic) could be plugged in later by writing a single new file — no changes to the rest of the codebase.
Containerisation
Docker packages the entire application and its dependencies into isolated containers. Docker Compose orchestrates all the containers (the app, Postgres, and Redis) so the entire system starts with a single command.
Dashboard
Streamlit with Plotly charts provides a visual dashboard where you can see spending, latency, model usage, and quality metrics in real time. Streamlit makes it easy to build data-focused web apps in Python.
Code Quality & CI
pytest runs the automated test suite. All tests mock (simulate) the Gemini API so no real AI calls are made during testing, which means tests are fast, free, and deterministic.
GitHub Actions provides continuous integration (CI). Every time code is pushed, the system automatically runs linting, type-checking, and all tests. If anything fails, the build is marked red and the code is not merged.

7. What the System Tracks


Every request that passes through the router is logged with the following information:
Data Point
What It Means
Model used
Which Gemini model handled the request
Complexity label
Whether the classifier deemed it simple, medium, or complex
Token counts
Number of input and output tokens (word-fragments) consumed
Cost (USD)
Exact dollar cost of the request, calculated from token counts and model pricing
Latency (ms)
How long the AI took to respond, in milliseconds
Prompt hash
A scrambled fingerprint of the question (the actual text is not stored, for privacy)
Quality score
A human-submitted rating (1–5) of the answer quality


This data is available through two API endpoints: one for browsing individual requests and one for aggregated metrics (total spend, average latency, quality scores broken down by model and time window).
8. The Dashboard


The Streamlit dashboard provides a visual, browser-based interface to explore the data. It has two main tabs:
Overview Tab — Displays headline KPIs (total requests, total spend, average latency, error count), bar charts of requests and costs per model, and a cost-versus-quality scatter plot that visualises the core tradeoff the router optimises for.
Request Explorer Tab — A filterable, searchable table of every request that has been routed. Users can filter by model, time range, or complexity label. The data can be exported as a CSV file.
The dashboard reads from the same API endpoints that any other application would use, which demonstrates a clean separation between the data layer and the presentation layer.

9. How to Run It


The system is designed to start with a single command. The only prerequisites are Docker (a tool for running software in containers) and a free Google Gemini API key.
Step 1: Copy the example environment file and add your Gemini API key.
Step 2: Run "docker compose up" in a terminal. This downloads and starts everything: the application, the database, and Redis.
Step 3: Open http://localhost:8000 to use the API, or http://localhost:8501 to see the dashboard.
No manual database setup, no complex configuration. The philosophy is: if it takes more than one command to run, it is too complicated.
10. Project Structure


The codebase is organised into distinct layers, each with a clear responsibility. This is called a "layered architecture" and is considered a best practice in professional software engineering.
API Layer (app/api/) — Handles incoming web requests and outgoing responses. This is the front door of the application.
Services Layer (app/services/) — Contains the business logic — the orchestration of classifying, routing, calling the AI, and logging results.
Core Layer (app/core/) — Houses the classifier, pricing calculations, and quality scoring logic. Pure logic with no web or database dependencies.
Providers Layer (app/providers/) — The abstract interface for AI model providers plus the concrete Gemini implementation. New providers are added here without touching anything else.
Database Layer (app/db/, app/models/) — Database connection management and the data models that define what gets stored.
Observability (app/observability/) — Structured logging (JSON-formatted, machine-readable) and request tracing so every request can be followed through the system.
11. Quality & Testing


Reliability is enforced through multiple layers of automated checking:
Automated tests (pytest) — Every major feature has tests that verify it works correctly. All AI calls are simulated so tests run instantly and for free.
Linting (ruff) — Automatically checks the code for style issues, potential bugs, and inconsistencies.
Type checking (mypy) — Verifies that variables and functions are used with the correct data types, catching a whole class of bugs before the code ever runs.
Continuous Integration (GitHub Actions) — Every code change triggers all of the above automatically. If any check fails, the change is blocked.
The result is a codebase where problems are caught early and automatically, not discovered in production.

12. What Could Come Next


The system is built as a complete MVP (Minimum Viable Product), but the architecture deliberately leaves room for future enhancements:
Streaming responses — Deliver AI answers word-by-word as they are generated, rather than waiting for the full response.
Multi-provider support — Add OpenAI (GPT-4) or Anthropic (Claude) as alternative AI providers alongside Gemini.
Prompt caching — Use Redis to cache answers for repeated questions, avoiding duplicate AI calls entirely.
Authentication & multi-tenancy — Allow multiple users or teams with separate API keys, usage tracking, and billing.
AI-as-judge quality scoring — Use a second AI model to automatically evaluate the quality of each answer, removing the need for human scoring.
Cloud deployment — Deploy to a cloud provider (AWS, GCP, or similar) for production use.
13. Summary


The Multi-Model Router is a complete, production-grade software system that solves a real problem facing every team that uses AI: how to control costs without sacrificing quality. It does this by inspecting each request, deciding how complex it is, and sending it to the cheapest AI model that can handle it. Every decision is logged and measurable.
The project demonstrates:
Product thinking — A clear problem statement, defined success metrics, and disciplined scope control.
Systems design — A layered, extensible architecture with clean separation of concerns.
Full-stack engineering — API design, database management, containerisation, CI/CD pipelines, and a visual dashboard.
Cost engineering — The core value proposition, backed by measurable data.
Software quality — Automated testing, linting, type checking, and continuous integration.



For the full source code, visit: github.com/Vickkywhyte/Multi-Model-Router

