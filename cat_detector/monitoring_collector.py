"""Thread-safe monitoring data collector for real-time debugging"""

import threading
import time
import cv2
import io
from typing import Optional, List, Dict, Any
from collections import deque


class MonitoringCollector:
    """Thread-safe collector for monitoring metrics and frame data"""

    def __init__(self, max_history: int = 100):
        """Initialize the monitoring collector
        
        Args:
            max_history: Maximum number of historical entries to keep
        """
        self._lock = threading.Lock()
        self.max_history = max_history
        
        # Current frame (JPEG encoded)
        self._current_frame_jpeg: Optional[bytes] = None
        self._current_frame_timestamp: float = 0.0
        
        # Performance metrics
        self._processing_times = deque(maxlen=max_history)
        self._fps_history = deque(maxlen=max_history)
        self._frame_count = 0
        self._start_time = time.time()
        
        # Detection history
        self._detections_history = deque(maxlen=max_history)
        
        # Queue status
        self._db_queue_size = 0
        self._db_queue_wait_time = 0.0
        self._file_queue_size = 0
        self._file_queue_wait_time = 0.0
        
        # Timing breakdown (last frame)
        self._timing_breakdown = {
            'frame_read': 0.0,
            'resize': 0.0,
            'detection': 0.0,
            'mqtt_publish': 0.0,
            'db_queue_wait': 0.0,
            'file_queue_wait': 0.0,
            'total': 0.0,
            'frame_age': 0.0  # Age of frame when processed (time between capture and processing)
        }
        
        # System status
        self._is_streaming = False
        self._last_frame_time = 0.0
        self._frames_skipped = 0
        self._total_frames_processed = 0
        self._frame_age = 0.0  # Current frame age in seconds
        self._frame_age_history = deque(maxlen=max_history)  # History of frame ages

    def update_frame(self, frame, timestamp: Optional[float] = None):
        """Update the current frame (JPEG encoded for web display)
        
        Args:
            frame: OpenCV frame (numpy array)
            timestamp: Optional timestamp, defaults to current time
        """
        if frame is None:
            return
            
        try:
            # Encode frame as JPEG (lower quality for web streaming)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
            success, buffer = cv2.imencode('.jpg', frame, encode_param)
            if success:
                with self._lock:
                    self._current_frame_jpeg = buffer.tobytes()
                    self._current_frame_timestamp = timestamp or time.time()
                    self._last_frame_time = self._current_frame_timestamp
        except Exception as e:
            print(f"⚠️  Error encoding frame for monitoring: {e}")

    def update_processing_time(self, processing_time: float):
        """Update processing time metrics
        
        Args:
            processing_time: Time taken to process a frame in seconds
        """
        with self._lock:
            self._processing_times.append(processing_time)
            self._total_frames_processed += 1
            if processing_time > 0:
                fps = 1.0 / processing_time
                self._fps_history.append(fps)
            self._frame_count += 1

    def update_timing_breakdown(self, timing: Dict[str, float]):
        """Update detailed timing breakdown for the last frame
        
        Args:
            timing: Dictionary with timing components:
                - frame_read: Time to read frame from stream
                - resize: Time to resize frame
                - detection: Time for YOLO detection
                - mqtt_publish: Time to publish MQTT message
                - db_queue_wait: Time waiting in DB queue
                - file_queue_wait: Time waiting in file queue
                - total: Total processing time
                - frame_age: Age of frame when processed (optional)
        """
        with self._lock:
            self._timing_breakdown.update(timing)
            # Track frame age if provided
            if 'frame_age' in timing:
                self._frame_age = timing['frame_age']
                self._frame_age_history.append(timing['frame_age'])

    def update_frame_age(self, frame_age: float):
        """Update the current frame age
        
        Args:
            frame_age: Age of the current frame in seconds (time between capture and now)
        """
        with self._lock:
            self._frame_age = frame_age
            self._frame_age_history.append(frame_age)
            # Also update timing breakdown
            self._timing_breakdown['frame_age'] = frame_age

    def add_detection(self, class_name: str, confidence: float, bbox: List[float], 
                     timestamp: str, detection_time: float):
        """Add a new detection to the history
        
        Args:
            class_name: Detected class name (e.g., 'Cat', 'Person')
            confidence: Detection confidence (0.0-1.0)
            bbox: Bounding box [x1, y1, x2, y2]
            timestamp: Detection timestamp string
            detection_time: Time taken for detection in seconds
        """
        detection = {
            'class_name': class_name,
            'confidence': confidence,
            'bbox': bbox,
            'timestamp': timestamp,
            'detection_time': detection_time,
            'recorded_at': time.time()
        }
        with self._lock:
            self._detections_history.append(detection)

    def update_queue_status(self, db_queue_size: int, db_queue_wait: float,
                           file_queue_size: int, file_queue_wait: float):
        """Update queue status information
        
        Args:
            db_queue_size: Current size of database queue
            db_queue_wait: Average wait time in DB queue
            file_queue_size: Current size of file queue
            file_queue_wait: Average wait time in file queue
        """
        with self._lock:
            self._db_queue_size = db_queue_size
            self._db_queue_wait_time = db_queue_wait
            self._file_queue_size = file_queue_size
            self._file_queue_wait_time = file_queue_wait

    def set_streaming_status(self, is_streaming: bool):
        """Update streaming status
        
        Args:
            is_streaming: Whether the stream is currently active
        """
        with self._lock:
            self._is_streaming = is_streaming

    def increment_frames_skipped(self, count: int = 1):
        """Increment the count of skipped frames
        
        Args:
            count: Number of frames skipped
        """
        with self._lock:
            self._frames_skipped += count

    def get_current_frame(self) -> Optional[bytes]:
        """Get the current frame as JPEG bytes (thread-safe)
        
        Returns:
            JPEG-encoded frame bytes or None
        """
        with self._lock:
            return self._current_frame_jpeg

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics (thread-safe)
        
        Returns:
            Dictionary with performance metrics
        """
        with self._lock:
            processing_times_list = list(self._processing_times)
            fps_list = list(self._fps_history)
            
            avg_processing_time = (sum(processing_times_list) / len(processing_times_list) 
                                 if processing_times_list else 0.0)
            avg_fps = (sum(fps_list) / len(fps_list) 
                      if fps_list else 0.0)
            min_processing_time = min(processing_times_list) if processing_times_list else 0.0
            max_processing_time = max(processing_times_list) if processing_times_list else 0.0
            
            uptime = time.time() - self._start_time
            
            # Calculate frame age statistics
            frame_age_list = list(self._frame_age_history)
            avg_frame_age = (sum(frame_age_list) / len(frame_age_list) 
                           if frame_age_list else 0.0)
            max_frame_age = max(frame_age_list) if frame_age_list else 0.0
            
            return {
                'fps': avg_fps,
                'current_fps': fps_list[-1] if fps_list else 0.0,
                'avg_processing_time': avg_processing_time,
                'min_processing_time': min_processing_time,
                'max_processing_time': max_processing_time,
                'total_frames_processed': self._total_frames_processed,
                'frames_skipped': self._frames_skipped,
                'uptime': uptime,
                'is_streaming': self._is_streaming,
                'last_frame_time': self._last_frame_time,
                'frame_age': self._frame_age,
                'avg_frame_age': avg_frame_age,
                'max_frame_age': max_frame_age
            }

    def get_detections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent detections (thread-safe)
        
        Args:
            limit: Maximum number of detections to return
            
        Returns:
            List of detection dictionaries
        """
        with self._lock:
            return list(self._detections_history)[-limit:]

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status (thread-safe)
        
        Returns:
            Dictionary with queue status information
        """
        with self._lock:
            return {
                'db_queue': {
                    'size': self._db_queue_size,
                    'wait_time': self._db_queue_wait_time
                },
                'file_queue': {
                    'size': self._file_queue_size,
                    'wait_time': self._file_queue_wait_time
                }
            }

    def get_timing_breakdown(self) -> Dict[str, float]:
        """Get detailed timing breakdown (thread-safe)
        
        Returns:
            Dictionary with timing components
        """
        with self._lock:
            return self._timing_breakdown.copy()

    def get_status(self) -> Dict[str, Any]:
        """Get overall system status (thread-safe)
        
        Returns:
            Dictionary with system status
        """
        with self._lock:
            return {
                'is_streaming': self._is_streaming,
                'uptime': time.time() - self._start_time,
                'total_frames_processed': self._total_frames_processed,
                'frames_skipped': self._frames_skipped,
                'last_frame_time': self._last_frame_time,
                'current_time': time.time()
            }

    def get_all_data(self) -> Dict[str, Any]:
        """Get all monitoring data in one call (thread-safe)
        
        Returns:
            Dictionary with all monitoring data
        """
        return {
            'status': self.get_status(),
            'metrics': self.get_metrics(),
            'detections': self.get_detections(limit=20),
            'queues': self.get_queue_status(),
            'timing': self.get_timing_breakdown(),
            'timestamp': time.time()
        }

