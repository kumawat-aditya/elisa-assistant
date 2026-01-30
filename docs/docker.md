# Docker Management Guide

A comprehensive guide for managing Docker images and containers for ELISA.

---

## 📦 ELISA Docker Services

| Service  | Container Name | Image                              | Port |
| -------- | -------------- | ---------------------------------- | ---- |
| TTS      | elisa-tts      | `ghcr.io/coqui-ai/tts-cpu:v0.22.0` | 5002 |
| Duckling | elisa-duckling | `rasa/duckling:0.2.0.2-r3`         | 8000 |

---

## 🚀 Basic Operations

### Start Services

```bash
cd infra
docker-compose up -d
```

### Stop Services

```bash
cd infra
docker-compose down
```

### Restart Services

```bash
cd infra
docker-compose restart
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f tts
docker-compose logs -f duckling
```

---

## 🔍 Check Status

### List Running Containers

```bash
docker ps
```

### List All Containers (including stopped)

```bash
docker ps -a
```

### Check Container Health

```bash
docker inspect elisa-tts
docker inspect elisa-duckling
```

---

## 🛠️ Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker logs elisa-tts

# Remove and recreate
docker rm -f elisa-tts
cd infra && docker-compose up -d tts
```

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :5002
sudo lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml
# ports:
#   - "5003:5002"  # Use different host port
```

### Container Crashes on Startup

```bash
# Check logs
docker logs elisa-tts --tail 50

# Try running interactively to debug
docker run -it --rm ghcr.io/coqui-ai/tts-cpu:v0.22.0 bash
```

### Out of Disk Space

```bash
# Check Docker disk usage
docker system df

# Remove unused containers, images, volumes
docker system prune -a

# Remove only stopped containers
docker container prune

# Remove only unused images
docker image prune -a
```

---

## 🔄 Recreate from Scratch

### Complete Reset

```bash
# Stop and remove all ELISA containers
docker rm -f elisa-tts elisa-duckling

# Remove the images (forces re-download)
docker rmi ghcr.io/coqui-ai/tts-cpu:v0.22.0
docker rmi rasa/duckling:0.2.0.2-r3

# Recreate everything
cd infra && docker-compose up -d
```

### Pull Latest Images

```bash
cd infra
docker-compose pull
docker-compose up -d
```

---

## 📋 Common Commands Reference

| Action           | Command                       |
| ---------------- | ----------------------------- |
| Start services   | `docker-compose up -d`        |
| Stop services    | `docker-compose down`         |
| Restart services | `docker-compose restart`      |
| View logs        | `docker-compose logs -f`      |
| List running     | `docker ps`                   |
| List all         | `docker ps -a`                |
| Stop container   | `docker stop <name>`          |
| Start container  | `docker start <name>`         |
| Remove container | `docker rm <name>`            |
| Force remove     | `docker rm -f <name>`         |
| Container logs   | `docker logs <name>`          |
| Container shell  | `docker exec -it <name> bash` |
| List images      | `docker images`               |
| Remove image     | `docker rmi <image>`          |
| Pull image       | `docker pull <image>`         |
| System cleanup   | `docker system prune -a`      |
| Disk usage       | `docker system df`            |

---

## 🐳 Running Individual Services

### TTS Only (CPU)

```bash
docker run -d \
  --name elisa-tts \
  -p 5002:5002 \
  --entrypoint /bin/bash \
  ghcr.io/coqui-ai/tts-cpu:v0.22.0 \
  -c "python3 TTS/server/server.py --model_name tts_models/en/ljspeech/glow-tts"
```

### TTS Only (GPU)

```bash
docker run -d \
  --name elisa-tts-gpu \
  --gpus all \
  -p 5002:5002 \
  --entrypoint /bin/bash \
  ghcr.io/coqui-ai/tts:v0.22.0 \
  -c "python3 TTS/server/server.py --model_name tts_models/en/ljspeech/glow-tts --use_cuda true"
```

### Duckling Only

```bash
docker run -d \
  --name elisa-duckling \
  -p 8000:8000 \
  rasa/duckling:0.2.0.2-r3
```

---

## 🔒 Best Practices

1. **Always use specific image tags** (not `latest`)

   ```
   ✅ ghcr.io/coqui-ai/tts-cpu:v0.22.0
   ❌ ghcr.io/coqui-ai/tts-cpu:latest
   ```

2. **Use docker-compose** for consistent deployments

3. **Check logs** before troubleshooting

   ```bash
   docker logs elisa-tts --tail 100
   ```

4. **Backup data** before removing containers with volumes

5. **Monitor resources**
   ```bash
   docker stats
   ```

---

## 🆘 Getting Help

```bash
# Docker help
docker --help
docker-compose --help

# Specific command help
docker run --help
docker logs --help
```
