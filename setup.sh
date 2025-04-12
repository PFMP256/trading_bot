#!/bin/bash

# Exit on error
set -e

echo "========================================"
echo "Trading Bot Setup Script"
echo "========================================"

# Update system and install dependencies
echo "Installing Docker and docker-compose if not already installed..."
if ! command -v docker &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
    echo "Docker installed. You may need to log out and back in for group changes to take effect."
fi

if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed."
fi


# Create logs directory if it doesn't exist
mkdir -p logs

# Create a start and stop script
echo "Creating start and stop scripts..."
cat > start.sh << EOF
#!/bin/bash
docker-compose up -d
echo "Trading bot started."
echo "To view logs: docker-compose logs -f"
EOF

cat > stop.sh << EOF
#!/bin/bash
docker-compose down
echo "Trading bot stopped."
EOF

chmod +x start.sh stop.sh

echo "========================================"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your API keys and preferences: nano .env"
echo "2. Start the trading bot: ./start.sh"
echo "3. View logs: docker-compose logs -f"
echo "4. Stop the bot: ./stop.sh"
echo "========================================"
