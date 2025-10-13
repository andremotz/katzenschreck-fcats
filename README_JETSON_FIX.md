# Jetson Installation Fix

## Problem

Beim Ausführen auf dem Jetson mit dem `ultralytics:jetpack5` Docker Container treten folgende Fehler auf:

1. **OpenCV DictValue Fehler**: `AttributeError: module 'cv2.dnn' has no attribute 'DictValue'`
2. **Puccinialin Dependency Fehler**: `ERROR: Could not find a version that satisfies the requirement puccinialin`

## Lösung

### Option 1: Docker Container verwenden (Empfohlen)

1. **Container neu bauen und starten**:
   ```bash
   ./start_jetson_docker.sh
   ```

2. **Logs überwachen**:
   ```bash
   docker logs -f katzenschreck
   ```

### Option 2: Bestehenden Container reparieren

Falls Sie bereits im `ultralytics:jetpack5` Container sind:

1. **Fix-Script ausführen**:
   ```bash
   ./fix_jetson_container.sh
   ```

2. **Oder manuell reparieren**:
   ```bash
   # OpenCV reparieren
   pip uninstall -y opencv-python-headless
   pip install opencv-python==4.8.1.78
   
   # Zusätzliche Dependencies installieren
   pip install paho-mqtt==1.6.1 mysql-connector-python==8.0.33
   
   # Anwendung testen
   python3 -m cat_detector.main /katzenschreck/results
   ```

## Was wurde geändert

1. **Dockerfile.jetson**:
   - Verwendet `ultralytics:jetpack5` als Base Image
   - Entfernt `opencv-python-headless` und installiert `opencv-python==4.8.1.78`
   - Installiert nur zusätzliche Dependencies (paho-mqtt, mysql-connector-python)
   - Verwendet `/katzenschreck` als Working Directory

2. **requirements_jetson.txt**:
   - Vereinfacht auf nur die notwendigen zusätzlichen Dependencies
   - OpenCV Version auf 4.8.1.78 aktualisiert

3. **docker-compose.jetson.yml**:
   - Pfade auf `/katzenschreck` angepasst

## Warum funktioniert das?

- Das `ultralytics:jetpack5` Image enthält bereits alle notwendigen Dependencies
- Das Problem war, dass `opencv-python-headless` verwendet wurde, welches `cv2.dnn.DictValue` nicht unterstützt
- Durch die Installation der vollständigen `opencv-python` Version wird das Problem behoben
- Das `puccinialin` Problem entsteht durch veraltete ultralytics Dependencies, die im Base Image bereits korrekt sind

## Verifikation

Nach der Reparatur sollten folgende Tests erfolgreich sein:

```bash
# OpenCV testen
python3 -c "import cv2; print(f'OpenCV: {cv2.__version__}'); from cv2.dnn import DictValue; print('DictValue available')"

# Anwendung testen
python3 -c "from cat_detector.stream_processor import StreamProcessor; print('Import successful')"
```
