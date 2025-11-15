# DevContainer Configuration

**One-click development environment for AI Document Pipeline microservices.**

## 🎯 What is This?

This DevContainer provides a fully configured development environment with:
- ✅ All Python dependencies pre-installed
- ✅ Complete infrastructure (PostgreSQL, RabbitMQ, OpenSearch, MinIO, Ollama)
- ✅ VS Code extensions and settings
- ✅ Code formatting and linting tools
- ✅ Consistent environment across all developers

## 🚀 Quick Start

### Prerequisites

1. **VS Code** - Download from [code.visualstudio.com](https://code.visualstudio.com/)
2. **Docker Desktop** - Download from [docker.com](https://www.docker.com/products/docker-desktop)
3. **Remote Containers Extension** - Install from VS Code marketplace

### Getting Started

1. **Open in DevContainer:**
   ```
   - Open VS Code
   - Press F1 or Cmd/Ctrl+Shift+P
   - Type "Dev Containers: Reopen in Container"
   - Wait for container to build (first time: ~5-10 minutes)
   ```

2. **Container builds automatically:**
   - Downloads base images
   - Installs system dependencies
   - Installs Python packages
   - Configures all infrastructure services
   - Runs post-create setup

3. **Start coding:**
   ```bash
   # Terminal opens inside container automatically
   # All services are running and ready
   ```

## 📦 What's Included

### Infrastructure Services

All services are automatically started and configured:

| Service | Port | Purpose | Credentials |
|---------|------|---------|-------------|
| **PostgreSQL** | 5432 | Document metadata | postgres/devpassword |
| **RabbitMQ** | 5672 | Message broker | admin/password |
| **RabbitMQ UI** | 15672 | Management console | admin/password |
| **Redis** | 6379 | Cache | (no auth) |
| **OpenSearch** | 9200 | Semantic search | (no auth) |
| **MinIO** | 9000 | Object storage | minioadmin/minioadmin |
| **MinIO Console** | 9001 | Storage UI | minioadmin/minioadmin |
| **Ollama** | 11434 | Local LLM | (no auth) |

### VS Code Extensions

Pre-installed extensions:

**Python Development:**
- Python (Pylance, debugging)
- Black formatter
- isort (import sorting)
- Flake8 linter

**Docker & Containers:**
- Docker
- Remote Containers

**Database:**
- SQLTools
- PostgreSQL driver

**Git:**
- GitLens

**Utilities:**
- YAML support
- Markdown support
- REST Client
- Error Lens
- Path Intellisense

### Python Tools

Pre-installed development tools:
- `black` - Code formatter
- `isort` - Import organizer
- `flake8` - Linter
- `pylint` - Code analyzer
- `mypy` - Type checker
- `pytest` - Testing framework
- `ipython` - Interactive Python
- `rich` - Beautiful terminal output
- `httpie` - HTTP client

### Docker CLI

Docker commands work inside the container:
```bash
docker ps
docker-compose up
docker logs
```

## 🔧 Configuration

### devcontainer.json

Main configuration file defining:
- Docker Compose file to use
- VS Code extensions
- Port forwarding
- Environment variables
- Post-create commands

### docker-compose.yml

Defines all infrastructure services:
- Development container
- PostgreSQL database
- RabbitMQ message broker
- Redis cache
- OpenSearch for search
- MinIO for object storage
- Ollama for LLM inference

### Dockerfile

Defines the development container:
- Python 3.11
- System dependencies
- Development tools
- User configuration

### post-create.sh

Runs after container is created:
- Installs Python dependencies
- Waits for services to be ready
- Creates .env file
- Prints helpful information

## 🎓 Usage

### Starting Microservices

```bash
# Start all microservices
./scripts/start_all.sh

# Start individual services
cd services/ingestion && python service.py
cd services/classification-worker && python worker.py
```

### Running Tests

```bash
# All tests
pytest tests/

# Specific test
pytest tests/test_api_search.py

# With coverage
pytest --cov=src tests/
```

### Database Access

```bash
# Connect to PostgreSQL
psql -h postgres -U postgres -d documents

# Using environment variable
PGPASSWORD=devpassword psql -h postgres -U postgres -d documents
```

### RabbitMQ Management

Open in browser: http://localhost:15672
- Username: `admin`
- Password: `password`

View:
- Queues and messages
- Exchanges and bindings
- Connections and channels
- Message rates and stats

### MinIO Console

Open in browser: http://localhost:9001
- Username: `minioadmin`
- Password: `minioadmin`

Manage:
- Buckets and objects
- Upload/download files
- Access policies
- Monitoring

### Ollama Models

Pull required models:
```bash
# Pull vision model for classification
docker exec -it $(docker ps -q -f name=ollama) ollama pull llama3.2-vision:11b

# Pull text model for extraction
docker exec -it $(docker ps -q -f name=ollama) ollama pull llama3.2:3b

# List installed models
docker exec -it $(docker ps -q -f name=ollama) ollama list
```

## 🛠️ Customization

### Adding VS Code Extensions

Edit `.devcontainer/devcontainer.json`:
```json
{
  "customizations": {
    "vscode": {
      "extensions": [
        "your-extension-id"
      ]
    }
  }
}
```

### Adding Python Packages

Edit `requirements.txt` and rebuild:
```bash
# Add package to requirements.txt
echo "numpy==1.24.0" >> requirements.txt

# Rebuild container
F1 -> "Dev Containers: Rebuild Container"
```

### Changing Service Versions

Edit `.devcontainer/docker-compose.yml`:
```yaml
postgres:
  image: postgres:16-alpine  # Changed from 15
```

## 🔍 Troubleshooting

### Container Won't Start

**Issue:** Container build fails
**Solution:**
```bash
# Remove old containers and volumes
docker-compose -f .devcontainer/docker-compose.yml down -v

# Rebuild from scratch
F1 -> "Dev Containers: Rebuild Container Without Cache"
```

### Services Not Ready

**Issue:** PostgreSQL/RabbitMQ connection fails
**Solution:**
```bash
# Check service status
docker-compose -f .devcontainer/docker-compose.yml ps

# View service logs
docker-compose -f .devcontainer/docker-compose.yml logs postgres
docker-compose -f .devcontainer/docker-compose.yml logs rabbitmq

# Restart services
docker-compose -f .devcontainer/docker-compose.yml restart postgres
```

### Port Already in Use

**Issue:** "Port 5432 is already allocated"
**Solution:**
```bash
# Stop conflicting service on host
# macOS/Linux:
sudo lsof -i :5432
sudo kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "5433:5432"  # Changed from 5432:5432
```

### Slow Performance

**Issue:** Container is slow
**Solution:**
1. Increase Docker Desktop resources:
   - Memory: 8GB minimum
   - CPUs: 4 cores minimum
   - Disk: 50GB minimum

2. Use named volumes instead of bind mounts (already configured)

3. Exclude large directories:
   ```json
   {
     "mounts": [
       "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=cached"
     ]
   }
   ```

### Python Import Errors

**Issue:** `ModuleNotFoundError`
**Solution:**
```bash
# Verify PYTHONPATH
echo $PYTHONPATH  # Should be /workspace

# Reinstall dependencies
pip install -r requirements.txt

# Install in editable mode (if needed)
pip install -e .
```

## 📊 Resource Usage

Typical resource usage:

| Component | Memory | CPU | Disk |
|-----------|--------|-----|------|
| Dev Container | 500MB | 10% | 2GB |
| PostgreSQL | 100MB | 5% | 500MB |
| RabbitMQ | 150MB | 5% | 200MB |
| Redis | 50MB | 2% | 100MB |
| OpenSearch | 1GB | 15% | 1GB |
| MinIO | 100MB | 5% | 500MB |
| Ollama | 2GB | 20% | 10GB (with models) |
| **Total** | **~4GB** | **~60%** | **~15GB** |

**Recommended:**
- RAM: 8GB minimum, 16GB preferred
- CPU: 4 cores minimum, 8 cores preferred
- Disk: 50GB free space

## 🔐 Security

**Development Only - Not for Production!**

This DevContainer uses default credentials for ease of development:
- PostgreSQL: `postgres/devpassword`
- RabbitMQ: `admin/password`
- MinIO: `minioadmin/minioadmin`

**For production:**
- Use strong, unique passwords
- Enable SSL/TLS
- Restrict network access
- Enable authentication on all services
- Use secrets management

## 🚀 Advanced Usage

### Multiple Terminals

Open multiple terminals in the container:
```bash
# Terminal 1: Run API
cd services/ingestion && python service.py

# Terminal 2: Run worker
cd services/classification-worker && python worker.py

# Terminal 3: Monitor logs
docker-compose -f docker-compose-microservices.yml logs -f
```

### Debugging

VS Code debugging is configured:
```bash
# Set breakpoint in code
# Press F5 to start debugging
# Choose "Python: Current File" or create launch.json
```

### Git Operations

Git is available inside the container:
```bash
git status
git add .
git commit -m "Your message"
git push
```

### Docker Compose

All services can be managed with docker-compose:
```bash
# View all services
docker-compose -f .devcontainer/docker-compose.yml ps

# Restart a service
docker-compose -f .devcontainer/docker-compose.yml restart postgres

# View logs
docker-compose -f .devcontainer/docker-compose.yml logs -f rabbitmq

# Scale a service (if supported)
docker-compose -f .devcontainer/docker-compose.yml up -d --scale worker=3
```

## 📚 Documentation

- **Microservices:** [README_MICROSERVICES.md](../README_MICROSERVICES.md)
- **Quick Start:** [MICROSERVICES_QUICK_START.md](../MICROSERVICES_QUICK_START.md)
- **Architecture:** [EVENT_DRIVEN_ARCHITECTURE.md](../EVENT_DRIVEN_ARCHITECTURE.md)
- **SQLModel:** [SQLMODEL_INTEGRATION.md](../SQLMODEL_INTEGRATION.md)
- **Deployment:** [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)

## 🤝 Contributing

To modify the DevContainer:
1. Edit configuration files in `.devcontainer/`
2. Rebuild: `F1 -> Dev Containers: Rebuild Container`
3. Test changes
4. Commit and push

## 📝 Notes

- **First build takes 5-10 minutes** - Subsequent starts are fast (~30 seconds)
- **Data persists** - Database data survives container restarts
- **Code changes immediate** - Workspace is mounted, no rebuild needed
- **Extensions sync** - VS Code extensions persist across rebuilds

## ✨ Benefits

**One-Click Setup:**
- No manual dependency installation
- No configuration required
- Works on macOS, Windows, Linux

**Consistent Environment:**
- Same environment for all developers
- Same versions of all tools
- No "works on my machine" issues

**Isolated Development:**
- Won't affect host system
- Multiple projects can use different versions
- Easy to reset and start fresh

**Production-Like:**
- Same services as production
- Same network topology
- Test microservices architecture locally

---

**Ready to start?** Press `F1` → `Dev Containers: Reopen in Container` 🚀
