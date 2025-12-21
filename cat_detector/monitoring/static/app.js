// WebSocket connection for real-time updates
let ws = null;
let reconnectInterval = null;
let frameUpdateInterval = null;

// Initialize connection
function init() {
    connectWebSocket();
    startFrameUpdates();
}

// WebSocket connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/monitoring`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            if (message.type === 'update') {
                updateUI(message.data);
            }
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);
        // Reconnect after 3 seconds
        if (!reconnectInterval) {
            reconnectInterval = setInterval(() => {
                connectWebSocket();
            }, 3000);
        }
    };
}

// Update frame image (separate from WebSocket for better performance)
function startFrameUpdates() {
    const frameImg = document.getElementById('live-frame');
    let frameCounter = 0;
    
    frameUpdateInterval = setInterval(() => {
        frameCounter++;
        frameImg.src = `/api/frame?t=${frameCounter}`;
    }, 500); // Update every 500ms
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.textContent = 'Verbunden';
        statusEl.className = 'status-badge connected';
    } else {
        statusEl.textContent = 'Getrennt';
        statusEl.className = 'status-badge disconnected';
    }
}

// Update all UI elements
function updateUI(data) {
    updateMetrics(data.metrics);
    updateTiming(data.timing);
    updateQueues(data.queues);
    updateDetections(data.detections);
    updateStreamStatus(data.status);
}

// Update performance metrics
function updateMetrics(metrics) {
    document.getElementById('avg-fps').textContent = metrics.fps.toFixed(2);
    document.getElementById('current-fps').textContent = metrics.current_fps.toFixed(2);
    document.getElementById('avg-processing').textContent = metrics.avg_processing_time.toFixed(3) + 's';
    document.getElementById('min-processing').textContent = metrics.min_processing_time.toFixed(3) + 's';
    document.getElementById('max-processing').textContent = metrics.max_processing_time.toFixed(3) + 's';
    document.getElementById('total-frames').textContent = metrics.total_frames_processed;
    document.getElementById('frames-skipped').textContent = metrics.frames_skipped;
    document.getElementById('uptime').textContent = formatUptime(metrics.uptime);
}

// Update timing breakdown
function updateTiming(timing) {
    const container = document.getElementById('timing-waterfall');
    container.innerHTML = '';
    
    // Find max time for scaling
    const maxTime = Math.max(
        timing.frame_read || 0,
        timing.resize || 0,
        timing.detection || 0,
        timing.mqtt_publish || 0,
        timing.db_queue_wait || 0,
        timing.file_queue_wait || 0,
        timing.total || 0
    );
    
    const timingItems = [
        { label: 'Frame Read', value: timing.frame_read || 0 },
        { label: 'Resize', value: timing.resize || 0 },
        { label: 'Detection', value: timing.detection || 0 },
        { label: 'MQTT Publish', value: timing.mqtt_publish || 0 },
        { label: 'DB Queue Wait', value: timing.db_queue_wait || 0 },
        { label: 'File Queue Wait', value: timing.file_queue_wait || 0 },
        { label: 'Total', value: timing.total || 0, highlight: true }
    ];
    
    timingItems.forEach(item => {
        const bar = document.createElement('div');
        bar.className = 'timing-bar';
        
        const label = document.createElement('div');
        label.className = 'timing-label';
        label.textContent = item.label;
        
        const visual = document.createElement('div');
        visual.className = 'timing-visual';
        
        const fill = document.createElement('div');
        fill.className = 'timing-fill';
        const percentage = maxTime > 0 ? (item.value / maxTime) * 100 : 0;
        fill.style.width = percentage + '%';
        fill.textContent = item.value > 0 ? item.value.toFixed(3) + 's' : '';
        
        if (item.highlight) {
            fill.style.background = 'linear-gradient(90deg, #4caf50, #45a049)';
        }
        
        visual.appendChild(fill);
        
        const value = document.createElement('div');
        value.className = 'timing-value';
        value.textContent = item.value.toFixed(3) + 's';
        
        bar.appendChild(label);
        bar.appendChild(visual);
        bar.appendChild(value);
        container.appendChild(bar);
    });
}

// Update queue status
function updateQueues(queues) {
    document.getElementById('db-queue-size').textContent = queues.db_queue.size;
    document.getElementById('db-queue-wait').textContent = queues.db_queue.wait_time.toFixed(3) + 's';
    document.getElementById('file-queue-size').textContent = queues.file_queue.size;
    document.getElementById('file-queue-wait').textContent = queues.file_queue.wait_time.toFixed(3) + 's';
}

// Update detections list
function updateDetections(detections) {
    const container = document.getElementById('detections-list');
    
    if (detections.length === 0) {
        container.innerHTML = '<p class="no-data">Keine Detections verfügbar</p>';
        return;
    }
    
    container.innerHTML = detections.reverse().map(detection => {
        const timeAgo = formatTimeAgo(detection.recorded_at);
        return `
            <div class="detection-item">
                <div class="detection-info">
                    <div class="detection-class">${detection.class_name}</div>
                    <div class="detection-details">
                        <span>⏱️ ${detection.timestamp}</span>
                        <span>🕐 ${timeAgo}</span>
                        <span>⚡ ${detection.detection_time.toFixed(3)}s</span>
                        <span>📦 [${detection.bbox.map(v => v.toFixed(0)).join(', ')}]</span>
                    </div>
                </div>
                <div class="detection-confidence">${(detection.confidence * 100).toFixed(1)}%</div>
            </div>
        `;
    }).join('');
}

// Update stream status
function updateStreamStatus(status) {
    const statusEl = document.getElementById('stream-status');
    if (status.is_streaming) {
        statusEl.textContent = 'Stream: Aktiv';
        statusEl.className = 'status-badge streaming';
    } else {
        statusEl.textContent = 'Stream: Inaktiv';
        statusEl.className = 'status-badge';
    }
    
    // Update frame timestamp
    if (status.last_frame_time) {
        const frameTime = new Date(status.last_frame_time * 1000);
        document.getElementById('frame-timestamp').textContent = 
            frameTime.toLocaleTimeString('de-DE');
    }
}

// Format uptime
function formatUptime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

// Format time ago
function formatTimeAgo(timestamp) {
    const now = Date.now() / 1000;
    const diff = now - timestamp;
    
    if (diff < 60) {
        return `${Math.floor(diff)}s ago`;
    } else if (diff < 3600) {
        return `${Math.floor(diff / 60)}m ago`;
    } else {
        return `${Math.floor(diff / 3600)}h ago`;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);

