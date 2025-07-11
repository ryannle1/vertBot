![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)

# VertBot: Discord Stock Analysis & AI Assistant

---

## Introduction

VertBot is a powerful, modular Discord bot designed to provide real-time stock market analysis, deliver up-to-date financial news, and offer AI-driven insights—all within your favorite Discord channels.  
Built with extensibility in mind, VertBot leverages live market data APIs and integrates cutting-edge local Large Language Models (LLMs) such as DeepSeek via Ollama, enabling both factual reporting and conversational analysis for investors, traders, and finance communities.

---

## Purpose

The project aims to simplify financial research and empower Discord users to:

- Get **instant stock quotes** and daily closing prices for any ticker.
- Access the **latest financial news** relevant to tracked companies.
- Receive **summarized, AI-powered insights** about market trends and specific stocks.
- Automate daily/periodic reporting in selected channels.
- Interact with an intelligent assistant capable of explaining financial events, news, or trends in natural language.

VertBot is ideal for investing clubs, trading communities, or anyone who wants smarter, faster access to market information on Discord.

---

## Current Functionality

### Phase 1: Real-Time Market Data & News

- **Stock Quote Commands:**  
  - `!price <TICKER>` — Get the most recent closing price of a stock.
  - `!current <TICKER>` — Get the current live market price (if markets are open).
- **Financial News:**  
  - `!news <TICKER>` — Fetches the latest news headlines for the given company.
- **Automated Daily Reports:**  
  - Scheduled posts of closing prices and news in a designated channel at market close (4pm US Eastern).
  - Admins can set or change the report channel using `!setreportchannel`.
- **Error Handling & Permissions:**  
  - Clear user-facing error messages for invalid symbols, missing API keys, or command misuse.
  - Deletes command messages for a clean channel experience.

### Phase 2: AI Integration & Analysis (Phi + Ollama)

- **AI Q&A Command:**  
  - `!askai <QUESTION or TICKER>` — Summarizes and analyzes recent real news headlines for specified tickers using the Phi LLM (via Ollama).
  - Supports multiple tickers and case-insensitive detection.
- **Natural Language Summaries:**  
  - Phi model provides readable, actionable market summaries, trend analysis, and explanation of financial jargon or events.

### Robust Configuration

- Supports multiple servers (guilds), each with its own report channel.
- API keys and secrets are loaded securely from environment files (never committed to git).
- Modular, easy-to-extend directory structure.

---

## Directory Structure

```plaintext
vertBot/
├── ai/                 # LLM interfaces (e.g., DeepSeek)
│   └── deepseek_llm.py
├── api/                # Data and news API wrappers
│   ├── market_data.py
│   └── news_data.py
├── bot/                # Bot entrypoint, commands, utilities
│   ├── main.py
│   └── commands/
│       ├── price.py
│       ├── news.py
│       ├── ai.py
│       └── ...
├── config/             # Config and secrets (not in git)
│   └── secrets.env
├── requirements.txt    # Python dependencies
└── README.md

```
---

## How to Use

1. **Invite VertBot to Your Discord Server:**  
    Follow the standard Discord bot invitation process using your bot's OAuth2 URL.

2. **Configure API Keys:**  
    - Create a `.env` file in the **root** of your project directory (where you run the bot).
    - Add your required API keys (e.g., for market data and news providers).  
    - Example:
      ```env
      FINNHUB_API_KEY=your_api_key_here
      DISCORD_TOKEN=your_discord_token_here
      ```

3. **Run the Bot:**  
    - Install dependencies:  
      ```bash
      pip install -r requirements.txt
      ```
    - Start VertBot:  
      ```bash
      python -m bot.main
      ```

4. **Available Commands:**  
    - `!price <TICKER>` — Get the latest closing price.
    - `!current <TICKER>` — Get the current live price.
    - `!news <TICKER>` — Fetch recent news headlines.
    - `!askai <QUESTION or TICKER>` — Get AI-powered summaries or answers.
    - `!setreportchannel` — Set the channel for daily reports (admin only).

5. **Automated Reports:**  
    VertBot will post daily closing prices (with improved formatting) in the configured channel at market close. News is no longer included in the daily report to reduce clutter.

6. **AI Analysis:**  
    Use `!askai` to get natural language explanations, summaries, or trend analysis for stocks and financial news, powered by the Phi model running locally via Ollama.

---

## Running the Phi Model Locally with Ollama

VertBot uses the [Phi](https://ollama.com/library/phi) model for AI-powered features. To run the model locally:

1. **Install Ollama:**
   - Follow instructions at [Ollama's website](https://ollama.com/download) for your OS or use Docker (recommended for servers).

2. **Pull the Phi model (in Docker):**
   - If running Ollama in Docker, use:
     ```sh
     docker exec -it ollama ollama pull phi
     ```
   - If running Ollama natively, use:
     ```sh
     ollama pull phi
     ```

3. **Verify the model is available:**
   - List models in your container:
     ```sh
     docker exec -it ollama ollama list
     ```

4. **Configure VertBot to use the model:**
   - The bot is pre-configured to use `phi` by default. If you want to use a different model, set the `OLLAMA_MODEL` environment variable in your `.env` file.

5. **Start VertBot and Ollama:**
   - Make sure both the Ollama container and VertBot are running. The bot will connect to Ollama at `http://localhost:11434` by default (or as set in your `.env`).

---

## Roadmap & Future Plans

VertBot is designed for ongoing growth and adaptability. Planned enhancements include:

- **Expanded Data Sources:**  
    Integrate additional APIs for broader stock coverage, including international exchanges, ETFs, and cryptocurrencies.

- **Advanced Analytics:**  
    Add technical indicators, charting, and historical data analysis.

- **Custom Alerts:**  
    Enable users to set price or news alerts for specific tickers.

- **Portfolio Tracking:**  
    Allow users to track and analyze their own portfolios within Discord.

- **AI Model Flexibility:**  
    Support for more LLMs and easy switching between models (e.g., Dolphin-Phi, TinyLlama) for different hardware and use cases.

- **Improved Reporting:**  
    More customizable and visually appealing daily/weekly reports, with options for summary, highlights, and user preferences.

- **Community Feedback:**  
    Actively gather user suggestions to prioritize new features and data types.

Contributions and feature requests are welcome—help shape VertBot's future!

---

## Acknowledgements

VertBot leverages the following open-source tools and APIs:

- [discord.py](https://github.com/Rapptz/discord.py) — Python library for building Discord bots.
- [Finnhub](https://finnhub.io/) — Real-time stock market data and news API.
- [Ollama](https://ollama.com/) — Local LLM orchestration for AI-powered features (now using the Phi model by default).

Special thanks to the open-source community for their invaluable libraries and resources.

---

## Disclaimer

VertBot is intended for **personal, educational, and informational use only**.  
All data, news, and AI-generated insights provided by VertBot—including those from DeepSeek or other LLMs—**do not constitute financial advice**.  
Always consult a qualified financial advisor before making investment decisions.  
The developers and contributors of VertBot are not responsible for any actions taken based on the information or analysis provided by this bot.