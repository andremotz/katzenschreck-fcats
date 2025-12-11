"""Real-time monitoring server for the cat deterrent system"""

import os
import time
import cv2
import threading
import queue
from typing import Optional, Dict, Any
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import uvicorn


class MonitoringServer:
    """FastAPI-based monitoring server for real-time video streaming"""

    def __init__(self, monitoring_queue: queue.Queue, config, stream_processor):
        self.monitoring_queue = monitoring_queue
        self.config = config
        self.stream_processor = stream_processor
        self.app = FastAPI(title="Katzenschreck Monitoring")
        
        # Try different template directory paths (Docker vs local)
        template_dirs = [
            "cat_detector/templates",
            "/katzenschreck/cat_detector/templates",
            os.path.join(os.path.dirname(__file__), "templates")
        ]
        template_dir = None
        for td in template_dirs:
            if os.path.exists(td):
                template_dir = td
                break
        if not template_dir:
            # Use the directory where this file is located
            template_dir = os.path.join(os.path.dirname(__file__), "templates")
            # Create directory if it doesn't exist
            os.makedirs(template_dir, exist_ok=True)
        
        self.templates = Jinja2Templates(directory=template_dir)
        print(f"📁 Using template directory: {template_dir}")
        
        # Statistics tracking
        self.stats = {
            "last_detection": None,
            "last_detection_time": None,
            "detections_count_1min": 0,
            "detections_timestamps": [],
            "stream_connected": False,
            "last_frame_time": None,
            "fps": 0.0,
            "avg_processing_time": 0.0
        }
        self.stats_lock = threading.Lock()
        
        # Frame rate limiting for monitoring
        self.last_frame_sent_time = 0
        self.min_frame_interval = 1.0 / getattr(config, 'monitoring_fps', 5.0)
        
        self._setup_routes()
        self._start_stats_cleanup_thread()

    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            """Main monitoring interface"""
            return self.templates.TemplateResponse("monitoring.html", {"request": request})
        
        @self.app.get("/stream")
        async def stream():
            """MJPEG video stream endpoint"""
            return StreamingResponse(
                self._generate_mjpeg_stream(),
                media_type="multipart/x-mixed-replace; boundary=frame"
            )
        
        @self.app.get("/api/stats")
        async def get_stats():
            """Get current statistics as JSON"""
            with self.stats_lock:
                # Calculate FPS from processing times
                if self.stream_processor.processing_times:
                    avg_processing_time = sum(self.stream_processor.processing_times) / len(
                        self.stream_processor.processing_times
                    )
                    if avg_processing_time > 0:
                        fps = 1.0 / avg_processing_time
                    else:
                        fps = 0.0
                else:
                    fps = 0.0
                    avg_processing_time = 0.0
                
                # Clean old detection timestamps (older than 1 minute)
                current_time = time.time()
                self.stats["detections_timestamps"] = [
                    ts for ts in self.stats["detections_timestamps"]
                    if current_time - ts < 60
                ]
                self.stats["detections_count_1min"] = len(self.stats["detections_timestamps"])
                
                stats_copy = {
                    "last_detection": self.stats["last_detection"],
                    "last_detection_time": self.stats["last_detection_time"],
                    "detections_count_1min": self.stats["detections_count_1min"],
                    "stream_connected": self.stats["stream_connected"],
                    "fps": round(fps, 2),
                    "avg_processing_time": round(avg_processing_time, 3),
                    "confidence_threshold": self.config.confidence_threshold,
                    "camera_name": self.config.camera_name
                }
                return stats_copy

    def _generate_mjpeg_stream(self):
        """Generator function for MJPEG stream"""
        while True:
            try:
                # Get frame from queue with timeout
                try:
                    frame = self.monitoring_queue.get(timeout=1.0)
                except queue.Empty:
                    # Send a placeholder frame if queue is empty
                    # Create a simple "Waiting for frames..." frame
                    frame = self._create_placeholder_frame()
                
                # Frame rate limiting
                current_time = time.time()
                if current_time - self.last_frame_sent_time < self.min_frame_interval:
                    continue
                self.last_frame_sent_time = current_time
                
                # Update stats
                with self.stats_lock:
                    self.stats["stream_connected"] = True
                    self.stats["last_frame_time"] = time.time()
                
                # Encode frame as JPEG
                success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not success:
                    continue
                
                # Yield frame in MJPEG format
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
            except Exception as e:
                print(f"⚠️  Monitoring stream error: {e}")
                time.sleep(0.1)

    def _create_placeholder_frame(self):
        """Create a placeholder frame when no frames are available"""
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "Waiting for camera stream...", (50, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return frame

    def update_stats(self, detection_info: Optional[Dict[str, Any]] = None):
        """Update statistics (called from stream processor)"""
        with self.stats_lock:
            if detection_info:
                self.stats["last_detection"] = detection_info
                self.stats["last_detection_time"] = time.strftime('%Y-%m-%d %H:%M:%S')
                self.stats["detections_timestamps"].append(time.time())
                # Keep only last 100 timestamps
                if len(self.stats["detections_timestamps"]) > 100:
                    self.stats["detections_timestamps"].pop(0)

    def _start_stats_cleanup_thread(self):
        """Start background thread for cleaning up old statistics"""
        def cleanup_worker():
            while True:
                time.sleep(60)  # Cleanup every minute
                with self.stats_lock:
                    current_time = time.time()
                    # Remove timestamps older than 1 minute
                    self.stats["detections_timestamps"] = [
                        ts for ts in self.stats["detections_timestamps"]
                        if current_time - ts < 60
                    ]
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the monitoring server"""
        print(f"🌐 Starting monitoring server on http://{host}:{port}")
        uvicorn.run(self.app, host=host, port=port, log_level="warning")


def start_monitoring_server(monitoring_queue: queue.Queue, config, stream_processor, 
                            host: str = "0.0.0.0", port: int = 8080):
    """Start monitoring server in a separate thread"""
    server = MonitoringServer(monitoring_queue, config, stream_processor)
    server_thread = threading.Thread(
        target=server.run,
        args=(host, port),
        daemon=True
    )
    server_thread.start()
    # Give server a moment to start
    import time
    time.sleep(0.5)
    return server
