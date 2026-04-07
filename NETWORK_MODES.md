# Network Modes für Katzenschreck Docker

## Übersicht

Der Katzenschreck Container unterstützt zwei Network-Modi:

| Mode | Ports sichtbar? | RTSP Kompatibilität | Empfehlung |
|------|----------------|---------------------|------------|
| **host** (Default) | ❌ Nein | ✅ Voll kompatibel | Standard für Produktiv-Einsatz |
| **bridge** | ✅ Ja (`docker ps`) | ✅ Funktioniert (bei IP-Adressen) | Für bessere Übersicht/Debugging |

---

## Host Network Mode (Default)

**Verwendung:**
```bash
./start_jetson_docker.sh /path/to/config.txt
```

**Vorteile:**
- ✅ RTSP-Streams funktionieren mit Hostnames
- ✅ Keine Port-Konflikte (jeder Container nutzt eigenen Port)
- ✅ Einfachste Netzwerk-Konfiguration
- ✅ Beste Performance (kein NAT-Overhead)

**Nachteile:**
- ❌ Ports nicht in `docker ps` sichtbar
- ❌ Container teilen sich Host-Netzwerk-Stack

**Port-Übersicht:**
```bash
./show_containers.sh  # Zeigt Ports via Labels an
```

---

## Bridge Network Mode

**Verwendung:**
```bash
NETWORK_MODE=bridge ./start_jetson_docker.sh /path/to/config.txt
```

**Vorteile:**
- ✅ Ports in `docker ps` sichtbar (`0.0.0.0:8080->8080/tcp`)
- ✅ Bessere Container-Isolation
- ✅ Standard Docker-Netzwerk-Best-Practices

**Nachteile:**
- ⚠️ RTSP-Streams müssen IP-Adressen verwenden (keine Hostnames im LAN)
- ⚠️ Leichter Performance-Overhead durch NAT

**Beispiel docker ps Output:**
```
CONTAINER                  PORTS                           NETWORKS
katzenschreck-cam_wernberg 0.0.0.0:8080->8080/tcp         bridge
```

---

## Vergleich

### Host Network (aktuell bei cam_wernberg und cam_munich)
```bash
$ docker ps
CONTAINER                  PORTS    NETWORKS
katzenschreck-cam_wernberg          host      # Keine Ports sichtbar
```

Port muss aus Labels gelesen werden:
```bash
$ docker inspect katzenschreck-cam_wernberg \
    --format='{{index .Config.Labels "katzenschreck.monitoring.port"}}'
8080
```

### Bridge Network
```bash
$ docker ps
CONTAINER                  PORTS                      NETWORKS
katzenschreck-cam_wernberg 0.0.0.0:8080->8080/tcp    bridge    # ✅ Port sichtbar!
```

---

## Empfehlung

**Für Produktiv-Betrieb:**
- ✅ **Host Network** (Default) - Beste Kompatibilität und Performance

**Für Entwicklung/Debugging:**
- ✅ **Bridge Network** - Bessere Port-Übersicht in `docker ps`

**RTSP-Stream-Kompatibilität:**
- Beide Modi funktionieren, wenn RTSP-URLs IP-Adressen verwenden
- Bei Hostnames in RTSP-URLs: **nur Host Network** garantiert funktioniert

---

## Migration bestehender Container

### Von Host → Bridge

```bash
# Container stoppen
docker stop katzenschreck-cam_wernberg

# Mit Bridge-Mode neu starten
NETWORK_MODE=bridge ./start_jetson_docker.sh /path/to/config.txt
```

### Von Bridge → Host

```bash
# Container stoppen
docker stop katzenschreck-cam_wernberg

# Mit Host-Mode neu starten (Default)
./start_jetson_docker.sh /path/to/config.txt
```

---

## Troubleshooting

### Bridge Mode: RTSP Stream nicht erreichbar

**Problem:** RTSP-URL verwendet Hostname statt IP
```
rtsp_stream_url=rtsp://ipcam-terrasse.local:554/11
```

**Lösung:** IP-Adresse verwenden
```
rtsp_stream_url=rtsp://192.168.1.100:554/11
```

Oder: Zurück zu Host Network Mode

---

## Monitoring-Port-Übersicht

Beide Container-Modi exposieren den Monitoring-Port:

| Container | Config Port | Network Mode | Zugriff |
|-----------|------------|--------------|---------|
| cam_wernberg | 8080 | bridge | http://localhost:8080 |
| cam_munich | 8081 | host | http://localhost:8081 |

---

## Weitere Tools

**Container-Übersicht mit Ports:**
```bash
./show_containers.sh
```

**Docker ps mit Port-Informationen:**
```bash
./docker_ps_custom.sh
```

**Standard docker ps:**
```bash
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Networks}}"
```
