# Katzenschreck auf Jetson mit Source-kompiliertem PyTorch

Diese Anleitung erklärt, wie man Katzenschreck auf einem NVIDIA Jetson mit einem Docker-Image verwendet, das PyTorch von Source mit CUDA-Unterstützung kompiliert.

## ⚠️ Wichtige Hinweise

- **Build-Zeit**: Der Build dauert **3-5 Stunden** auf einem Jetson Nano!
- **Speicherplatz**: Benötigt mindestens 15-20 GB freien Speicherplatz
- **Stromversorgung**: Stelle sicher, dass der Jetson ausreichend mit Strom versorgt ist (5V/4A empfohlen)
- **Geduld**: Der Build-Prozess ist sehr ressourcenintensiv

## Warum Source-Build?

Dieses Dockerfile kompiliert PyTorch von Source, um:
- **Exakte Version**: PyTorch 2.1.0 mit CUDA 11.4 (wie in JETSON_PYTORCH_SETUP.md dokumentiert)
- **Vollständige CUDA-Unterstützung**: Garantiert, dass alle CUDA-Bibliotheken enthalten sind
- **Kontrolle**: Vollständige Kontrolle über den Build-Prozess
- **Reproduzierbarkeit**: Konsistente Installation auf verschiedenen Jetson-Geräten

## Voraussetzungen

1. NVIDIA Jetson mit JetPack 6.3 (R35) oder höher
2. Docker und nvidia-container-runtime installiert
3. Mindestens 20 GB freier Speicherplatz
4. Stabile Stromversorgung (5V/4A empfohlen)
5. Ausreichend Zeit (3-5 Stunden Build-Zeit)

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/andremotz/katzenschreck-fcats.git
cd katzenschreck-fcats
```

### 2. Config-Datei erstellen

```bash
cp config.txt.example config.txt
nano config.txt
```

Stelle sicher, dass `hardware_type=jetson` in `config.txt` gesetzt ist:

```
hardware_type=jetson
```

### 3. Docker Image bauen

**Option A: Mit Build-Script (empfohlen)**

```bash
./start_jetson_docker_source.sh
```

**Option B: Mit Docker Compose**

```bash
docker-compose -f docker-compose.jetson.source.yml build
```

**Option C: Manuell**

```bash
# Mit BuildKit für besseres Caching (empfohlen)
DOCKER_BUILDKIT=1 docker build -f Dockerfile.jetson.source -t katzenschreck:jetson-source .
```

### 4. Build-Prozess überwachen

Der Build-Prozess besteht aus mehreren Phasen:

1. **Python 3.11 Kompilierung** (30-60 Minuten)
2. **PyTorch Kompilierung** (2-4 Stunden) ⏰
3. **torchvision Kompilierung** (30-60 Minuten)
4. **Final Image Assembly** (5-10 Minuten)

Du kannst den Fortschritt mit folgendem Befehl überwachen:

```bash
# In einem separaten Terminal
watch -n 5 'docker ps -a | grep katzenschreck-source'
```

Oder die Build-Logs in Echtzeit ansehen:

```bash
docker build -f Dockerfile.jetson.source -t katzenschreck:jetson-source . 2>&1 | tee build.log
```

## Verwendung

### Mit Docker Compose (empfohlen)

```bash
# Container starten
docker-compose -f docker-compose.jetson.source.yml up -d

# Logs ansehen
docker-compose -f docker-compose.jetson.source.yml logs -f

# Container stoppen
docker-compose -f docker-compose.jetson.source.yml down
```

### Mit Docker Run

```bash
docker run -d \
  --name katzenschreck-source \
  --runtime nvidia \
  --network host \
  -v $(pwd)/config.txt:/katzenschreck/config.txt:ro \
  -v $(pwd)/results:/katzenschreck/results \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  --restart unless-stopped \
  katzenschreck:jetson-source
```

## CUDA-Verifikation

Nach dem Build kannst du überprüfen, ob CUDA korrekt funktioniert:

```bash
# CUDA-Status prüfen
docker exec katzenschreck-source /usr/local/bin/python3.11 -c "
import torch
print(f'PyTorch Version: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
print(f'CUDA Version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')
print(f'Device Count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')
if torch.cuda.is_available():
    print(f'Device Name: {torch.cuda.get_device_name(0)}')
"

# CUDA-Bibliotheken prüfen
docker exec katzenschreck-source /usr/local/bin/python3.11 -c "
import torch
import os
lib_path = os.path.join(os.path.dirname(torch.__file__), 'lib')
files = os.listdir(lib_path) if os.path.exists(lib_path) else []
cuda_files = [f for f in files if 'cuda' in f.lower()]
print(f'CUDA libs found: {len(cuda_files)} files')
print(f'First 10: {cuda_files[:10]}')
"
```

**Erwartete Ausgabe:**
```
PyTorch Version: 2.1.0
CUDA Available: True
CUDA Version: 11.4
Device Count: 1
Device Name: Xavier (oder ähnlich)
CUDA libs found: [mehrere Dateien]
```

## Troubleshooting

### Build schlägt fehl: "out of memory"

- **Lösung**: Reduziere die Anzahl der parallelen Build-Jobs
  ```bash
  # Im Dockerfile, ändere:
  # make -j$(nproc)
  # zu:
  # make -j2
  ```

### Build schlägt fehl: "nvcc: command not found"

- **Problem**: CUDA ist nicht im PATH
- **Lösung**: Das Dockerfile sollte CUDA automatisch finden. Falls nicht, prüfe:
  ```bash
  docker run --rm nvcr.io/nvidia/l4t-base:r35.2.0 nvcc --version
  ```

### Build schlägt fehl: "CMake version too old"

- **Problem**: CMake Version < 3.18.0
- **Lösung**: Das Dockerfile installiert automatisch CMake 3.24.0. Falls es weiterhin fehlschlägt, prüfe:
  ```bash
  docker run --rm katzenschreck:jetson-source cmake --version
  ```

### Container startet, aber CUDA ist nicht verfügbar

1. **Prüfe NVIDIA Container Runtime:**
   ```bash
   docker run --rm --runtime nvidia nvcr.io/nvidia/l4t-base:r35.2.0 nvidia-smi
   ```

2. **Prüfe Container-Logs:**
   ```bash
   docker logs katzenschreck-source
   ```

3. **Prüfe CUDA im Container:**
   ```bash
   docker exec katzenschreck-source /usr/local/bin/python3.11 -c "import torch; print(torch.cuda.is_available())"
   ```

### Build dauert zu lange

- **Normal**: Der Build dauert 3-5 Stunden auf einem Jetson Nano
- **Tipp**: Verwende `screen` oder `tmux` für den Build-Prozess:
  ```bash
  screen -S docker_build
  docker build -f Dockerfile.jetson.source -t katzenschreck:jetson-source .
  # Drücke Ctrl+A, dann D zum Detachen
  ```

## Vergleich: Source vs. Pre-built Image

| Feature | Source Build | Pre-built (Dockerfile.jetson) |
|---------|--------------|-------------------------------|
| Build-Zeit | 3-5 Stunden | 5-10 Minuten |
| PyTorch Version | 2.1.0 (exakt) | Vom Base Image |
| CUDA-Garantie | ✅ Garantiert | ✅ (aus Base Image) |
| Kontrolle | ✅ Vollständig | ❌ Begrenzt |
| Speicherplatz | ~15-20 GB | ~5-8 GB |
| Wartung | Komplexer | Einfacher |

## Empfehlung

- **Verwende Source Build**, wenn:
  - Du die exakte PyTorch-Version 2.1.0 benötigst
  - Du Probleme mit dem Pre-built Image hast
  - Du vollständige Kontrolle über den Build-Prozess willst

- **Verwende Pre-built Image** (`Dockerfile.jetson`), wenn:
  - Du schnell starten willst
  - Die PyTorch-Version aus dem Base Image ausreicht
  - Du weniger Speicherplatz hast

## Auto-Start bei System-Boot

### Mit Docker Compose

```bash
# Docker Service aktivieren
sudo systemctl enable docker

# Restart-Policy ist bereits in docker-compose.yml gesetzt (unless-stopped)
```

### Mit Systemd Service

Erstelle `/etc/systemd/system/katzenschreck-source.service`:

```ini
[Unit]
Description=Katzenschreck Cat Detection System (Source Build)
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/youruser/katzenschreck
ExecStart=/usr/bin/docker-compose -f docker-compose.jetson.source.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.jetson.source.yml down
User=youruser

[Install]
WantedBy=multi-user.target
```

Aktivieren:

```bash
sudo systemctl daemon-reload
sudo systemctl enable katzenschreck-source.service
sudo systemctl start katzenschreck-source.service
```

## Updates

```bash
# Code aktualisieren
git pull

# Image neu bauen (dauert wieder 3-5 Stunden!)
docker-compose -f docker-compose.jetson.source.yml build

# Container neu starten
docker-compose -f docker-compose.jetson.source.yml up -d
```

## Weitere Informationen

- Siehe `JETSON_PYTORCH_SETUP.md` für native Installation ohne Docker
- Siehe `README_DOCKER_JETSON.md` für Pre-built Image Variante
- Siehe `README.md` für allgemeine Projekt-Dokumentation

