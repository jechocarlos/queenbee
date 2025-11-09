# QueenBee Setup Guide

## Prerequisites

- Python 3.14+
- Docker and Docker Compose
- Git

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/jechocarlos/queenbee.git
cd queenbee
```

### 2. Create Virtual Environment

```bash
python3.14 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 4. Set Up Environment

```bash
cp .env.example .env
```

Edit `.env` and set your database password:
```bash
DB_PASSWORD=your_secure_password
```

### 5. Start Docker Services

For local development (PostgreSQL + Ollama):
```bash
docker-compose -f docker-compose.local.yml up -d
```

Wait for services to be healthy:
```bash
docker-compose -f docker-compose.local.yml ps
```

### 6. Pull Ollama Model

```bash
docker exec -it queenbee-ollama ollama pull llama3.1:8b
```

This may take a few minutes depending on your internet connection.

### 7. Run Database Migrations

```bash
python scripts/migrate.py
```

You should see:
```
✓ Successfully applied 001_initial_schema.sql
✓ All migrations completed successfully
```

### 8. Start QueenBee

```bash
queenbee
```

Or run directly:
```bash
python -m queenbee.cli.main
```

## Verification

You should see:
```
🐝 QueenBee v1.0.0
Meta-Agent Orchestration System

✓ Session started: <uuid>
✓ Queen agent ready

You: 
```

## Example Interactions

### Simple Request
```
You: What's the capital of France?
🐝 Queen: Paris.
```

### Complex Request
```
You: Should I use microservices or a monolith for my startup?
🐝 Queen: [QueenBee] This is a complex multi-perspective question...
```

## Troubleshooting

### Ollama Not Available

```bash
# Check if Ollama is running
docker ps | grep ollama

# Check Ollama logs
docker logs queenbee-ollama

# Test Ollama directly
curl http://localhost:11434/api/tags
```

### Database Connection Failed

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs queenbee-postgres

# Test connection
docker exec -it queenbee-postgres psql -U queenbee -d queenbee -c "SELECT 1;"
```

### Model Not Found

```bash
# List available models
docker exec -it queenbee-ollama ollama list

# Pull the model again
docker exec -it queenbee-ollama ollama pull llama3.1:8b
```

## Stopping Services

```bash
# Stop QueenBee (Ctrl+C in the terminal)

# Stop Docker services
docker-compose -f docker-compose.local.yml down

# Stop and remove volumes (⚠️ deletes all data)
docker-compose -f docker-compose.local.yml down -v
```

## Development Mode

### Running Tests

```bash
pytest
pytest --cov=src/queenbee
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Viewing Logs

```bash
# Set LOG_LEVEL in .env
LOG_LEVEL=DEBUG

# Or pass when running
LOG_LEVEL=DEBUG queenbee
```

## Remote Database Setup

To use a remote PostgreSQL database:

1. Edit `.env`:
```bash
DB_HOST=your-remote-host.com
DB_SSL_MODE=require
```

2. Use remote compose file:
```bash
docker-compose -f docker-compose.remote.yml up -d
```

3. Run migrations pointing to remote DB:
```bash
python scripts/migrate.py
```

## Next Steps

- Explore the system prompts in `prompts/`
- Review configuration options in `config.yaml`
- Check the specification in `.github/SPECS.md`
- Read the development TODO in `.github/TODO.md`

## Support

- GitHub Issues: https://github.com/jechocarlos/queenbee/issues
- Documentation: `/docs` directory
- Specification: `.github/SPECS.md`
