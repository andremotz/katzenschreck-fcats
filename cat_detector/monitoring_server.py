"""FastAPI-based monitoring server for real-time debugging"""

import asyncio
import json
import threading
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import sys
import os

# Add the parent directory to the Python path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_detector.monitoring_collector import MonitoringCollector


class MonitoringServer:
    """FastAPI server for real-time monitoring"""

    def __init__(self, collector: MonitoringCollector, port: int = 8080):
        """Initialize the monitoring server
        
        Args:
            collector: MonitoringCollector instance
            port: Port to run the server on
        """
        self.collector = collector
        self.port = port
        self.app = FastAPI(title="Katzenschreck Monitoring", version="1.0.0")
        self.websocket_clients: Set[WebSocket] = set()
        self._setup_routes()
        self._broadcast_task = None
        self._server_thread = None
        self._running = False

    def _setup_routes(self):
        """Setup all API routes"""
        
        @self.app.get("/api/status")
        async def get_status():
            """Get system status"""
            return self.collector.get_status()

        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get performance metrics"""
            return self.collector.get_metrics()

        @self.app.get("/api/detections")
        async def get_detections(limit: int = 10):
            """Get recent detections"""
            return self.collector.get_detections(limit=limit)

        @self.app.get("/api/queues")
        async def get_queues():
            """Get queue status"""
            return self.collector.get_queue_status()

        @self.app.get("/api/timing")
        async def get_timing():
            """Get timing breakdown"""
            return self.collector.get_timing_breakdown()

        @self.app.get("/api/timing/history")
        async def get_timing_history(limit: int = 10):
            """Get historical timing breakdowns for profiling"""
            return self.collector.get_timing_history(limit=limit)

        @self.app.get("/api/frame")
        async def get_frame():
            """Get current frame as JPEG"""
            frame_jpeg = self.collector.get_current_frame()
            if frame_jpeg is None:
                raise HTTPException(status_code=404, detail="No frame available")
            return Response(content=frame_jpeg, media_type="image/jpeg")

        @self.app.get("/api/all")
        async def get_all():
            """Get all monitoring data"""
            return self.collector.get_all_data()

        @self.app.websocket("/ws/monitoring")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_clients.add(websocket)
            try:
                # Send initial data
                data = self.collector.get_all_data()
                await websocket.send_json({
                    "type": "update",
                    "timestamp": data["timestamp"],
                    "data": data
                })
                
                # Keep connection alive and wait for disconnect
                while True:
                    try:
                        # Wait for ping or disconnect
                        await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    except asyncio.TimeoutError:
                        # Send periodic update
                        data = self.collector.get_all_data()
                        await websocket.send_json({
                            "type": "update",
                            "timestamp": data["timestamp"],
                            "data": data
                        })
            except WebSocketDisconnect:
                pass
            finally:
                self.websocket_clients.discard(websocket)

        # Serve static files if directory exists
        static_dir = os.path.join(os.path.dirname(__file__), "monitoring", "static")
        if os.path.exists(static_dir):
            self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
            
            @self.app.get("/")
            async def index():
                """Serve the monitoring dashboard"""
                index_path = os.path.join(static_dir, "index.html")
                if os.path.exists(index_path):
                    return FileResponse(index_path)
                return {"message": "Monitoring dashboard not found"}

    async def _broadcast_updates(self):
        """Background task to broadcast updates to all WebSocket clients"""
        while self._running:
            try:
                if self.websocket_clients:
                    data = self.collector.get_all_data()
                    message = {
                        "type": "update",
                        "timestamp": data["timestamp"],
                        "data": data
                    }
                    # Send to all connected clients
                    disconnected = set()
                    for client in self.websocket_clients:
                        try:
                            await client.send_json(message)
                        except Exception:
                            disconnected.add(client)
                    
                    # Remove disconnected clients
                    for client in disconnected:
                        self.websocket_clients.discard(client)
                
                await asyncio.sleep(0.5)  # Update every 500ms
            except Exception as e:
                print(f"⚠️  Error in broadcast task: {e}")
                await asyncio.sleep(1)

    def _run_server(self):
        """Run the uvicorn server in a separate thread"""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="warning"
        )
        server = uvicorn.Server(config)
        asyncio.run(server.serve())

    def start(self):
        """Start the monitoring server in a background thread"""
        if self._running:
            return
        
        self._running = True
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        print(f"✅ Monitoring server started on http://localhost:{self.port}")

    def stop(self):
        """Stop the monitoring server"""
        self._running = False
        # Close all WebSocket connections
        for client in list(self.websocket_clients):
            try:
                asyncio.run(client.close())
            except Exception:
                pass
        self.websocket_clients.clear()
        print("Monitoring server stopped")

