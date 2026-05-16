# Bot Design Template 🤖

A clean, high-performance, and modular Discord bot template built with `discord.py`. This template is optimized for speed and low RAM usage, featuring a dynamic cog-loading system and RavenDB integration.

## 🚀 Features

- **Modular Architecture**: Automatically loads cogs from the `cogs/` directory.
- **RAM Optimized**: Aggressive memory management (disabled member cache, reduced message cache) to run efficiently on low-tier hosting.
- **RavenDB Integration**: Pre-configured for asynchronous NoSQL database management.
- **Web Server Built-in**: Includes a simple `aiohttp` web server for health checks (e.g., UptimeRobot or Render pings).
- **Docker Ready**: Includes a `Dockerfile` for easy deployment.
- **Environment Driven**: Uses `.env` for secure configuration.

## 🛠️ Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/EndSkiess/Bot-Design-Template.git
   cd Bot-Design-Template
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your tokens:
   ```bash
   cp .env.example .env
   ```

4. **Run the Bot**:
   ```bash
   python main.py
   ```

## 📁 Directory Structure

- `main.py`: Entry point of the bot.
- `cogs/`: Place your feature modules here (grouped by category).
- `data/`: Local data storage.
- `fonts/` & `pfp/`: Asset storage for dynamic image generation.
- `free.shizubot.client.certificate/`: RavenDB certificate storage.

## 🚢 Deployment

This template is ready for:
- **Render**: Uses `render.yaml` for automatic blueprints.
- **Fly.io**: Uses `fly.toml` for quick deployment.
- **Docker**: Build with `docker build -t my-bot .`.

---
Developed by [EndSkiess](https://github.com/EndSkiess)
