# Trading Bot

Cryptocurrency trading bot with Docker deployment support.

## Quick Setup

1. Clone this repository to your Ubuntu server
2. Navigate to the project directory
3. Run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

4. Edit the `.env` file with your API keys and trading preferences:

```bash
nano .env
```

5. Start the trading bot:

```bash
./start.sh
```

## Docker Deployment

The bot is configured to run in a Docker container. The setup script will:

- Install Docker and Docker Compose if needed
- Create necessary configuration files
- Set up environment variables

## Management Commands

- Start the bot: `./start.sh`
- View logs: `docker-compose logs -f`
- Stop the bot: `./stop.sh`
- Rebuild container: `docker-compose build`

## Configuration

Edit the `.env` file to configure:

- Binance API credentials
- Trading pairs
- Strategy parameters
- Risk management settings

## Troubleshooting

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Ensure your API keys have correct permissions
3. Verify server has a stable internet connection
4. Rebuild the container if dependencies changed: `docker-compose build --no-cache`