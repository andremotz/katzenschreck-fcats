"""Video stream processing for the cat deterrent system"""

import os
import time
import cv2
import sys
import threading
import queue
import copy

# Add the parent directory to the Python path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_detector.config import Config
from cat_detector.object_detector import ObjectDetector
from cat_detector.mqtt_handler import MQTTHandler
from cat_detector.database_handler import DatabaseHandler
from cat_detector.results_cleanup import cleanup_results_folder
from cat_detector.monitoring_collector import MonitoringCollector
from cat_detector.monitoring_server import MonitoringServer


class StreamProcessor:  # pylint: disable=too-few-public-methods
    """Main class for video stream processing"""

    def __init__(self, config: Config, output_dir: str):
        self.config = config
        self.output_dir = output_dir
        # Use configured model if available, otherwise auto-detect
        model_path = config.yolo_model if config.yolo_model else None
        self.detector = ObjectDetector(model_path=model_path, hardware_type=config.hardware_type)
        self.mqtt_handler = MQTTHandler(config)
        self.db_handler = DatabaseHandler(config)

        # Frame timing for hourly saving
        self.last_frame_save_time = 0
        self.frame_save_interval = 3600  # 3600 seconds = 1 hour

        # Performance monitoring for dynamic frame skipping
        self.processing_times = []  # Track last N processing times
        self.max_processing_times = 10  # Keep last 10 processing times
        self.target_fps = 1.0  # Target: process at least 1 frame per second
        self.max_processing_time = 1.0 / self.target_fps  # Max 1 second per frame
        self._total_frames_processed = 0  # Track total frames for monitoring frame updates

        # Background task queues for non-blocking operations
        self.db_queue = queue.Queue(maxsize=10)  # Limit queue size to prevent memory issues
        self.file_queue = queue.Queue(maxsize=10)
        
        # Monitoring setup (if enabled)
        self.monitoring_collector = None
        self.monitoring_server = None
        if config.monitoring_enabled:
            self.monitoring_collector = MonitoringCollector()
            self.monitoring_server = MonitoringServer(self.monitoring_collector, config.monitoring_port)
            self.monitoring_server.start()
            print(f"✅ Monitoring enabled on port {config.monitoring_port}")
        
        # Start background worker threads
        self._start_background_workers()

        # Create output directory
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _start_background_workers(self):
        """Starts background worker threads for non-blocking operations"""
        # Database worker thread
        db_worker = threading.Thread(target=self._db_worker, daemon=True)
        db_worker.start()
        
        # File save worker thread
        file_worker = threading.Thread(target=self._file_worker, daemon=True)
        file_worker.start()
        
        print("✅ Background workers started for non-blocking operations")

    def _db_worker(self):
        """Background worker thread for database operations"""
        while True:
            try:
                task_start_time = time.time()
                task = self.db_queue.get(timeout=1)
                if task is None:  # Shutdown signal
                    break
                queue_wait_time = time.time() - task_start_time
                frame, confidence, timestamp = task
                self.db_handler.save_frame_to_database(frame, confidence)
                print(f"✅ Background: Detection image saved to database (Confidence: {confidence:.2f})")
                
                # Update monitoring with queue wait time
                if self.monitoring_collector:
                    self.monitoring_collector.update_queue_status(
                        self.db_queue.qsize(),
                        queue_wait_time,
                        self.file_queue.qsize(),
                        0.0  # File queue wait time updated in file_worker
                    )
                
                self.db_queue.task_done()
            except queue.Empty:
                # Update monitoring even when queue is empty
                if self.monitoring_collector:
                    self.monitoring_collector.update_queue_status(
                        self.db_queue.qsize(),
                        0.0,
                        self.file_queue.qsize(),
                        0.0
                    )
                continue
            except Exception as e:
                print(f"⚠️  Database worker error: {e}")
                self.db_queue.task_done()

    def _file_worker(self):
        """Background worker thread for file operations"""
        while True:
            try:
                task_start_time = time.time()
                task = self.file_queue.get(timeout=1)
                if task is None:  # Shutdown signal
                    break
                queue_wait_time = time.time() - task_start_time
                annotated_frame, timestamp = task
                cleanup_results_folder(self.output_dir, self.config.usage_threshold)
                output_file = f'{self.output_dir}/frame_{timestamp}.jpg'
                cv2.imwrite(output_file, annotated_frame)
                print(f"✅ Background: Frame saved to {output_file}")
                
                # Update monitoring with queue wait time
                if self.monitoring_collector:
                    self.monitoring_collector.update_queue_status(
                        self.db_queue.qsize(),
                        0.0,  # DB queue wait time updated in db_worker
                        self.file_queue.qsize(),
                        queue_wait_time
                    )
                
                self.file_queue.task_done()
            except queue.Empty:
                # Update monitoring even when queue is empty
                if self.monitoring_collector:
                    self.monitoring_collector.update_queue_status(
                        self.db_queue.qsize(),
                        0.0,
                        self.file_queue.qsize(),
                        0.0
                    )
                continue
            except Exception as e:
                print(f"⚠️  File worker error: {e}")
                self.file_queue.task_done()

    def _save_detection(self, annotated_frame, timestamp: str):
        """Queues the detected frame for background saving (non-blocking)"""
        try:
            # Make a copy of the frame for the background thread
            frame_copy = copy.deepcopy(annotated_frame)
            self.file_queue.put_nowait((frame_copy, timestamp))
        except queue.Full:
            print("⚠️  File queue full, skipping frame save (non-critical)")
        except Exception as e:
            print(f"⚠️  Error queueing frame save: {e}")

    def _resize_frame_to_fullhd(self, frame):
        """Reduces frame resolution from 4K to Full HD (1920x1080)"""
        resize_start = time.time()
        height, width = frame.shape[:2]

        # Target resolution: Full HD (1920x1080)
        target_width = 1920
        target_height = 1080

        # Only resize if frame is larger than Full HD
        if width > target_width or height > target_height:
            resized_frame = cv2.resize(frame, (target_width, target_height),
                                     interpolation=cv2.INTER_AREA)
            print(f"Frame resized from {width}x{height} to "
                  f"{target_width}x{target_height}")
            resize_time = time.time() - resize_start
            # Update monitoring
            if self.monitoring_collector:
                timing = self.monitoring_collector.get_timing_breakdown()
                timing['resize'] = resize_time
                self.monitoring_collector.update_timing_breakdown(timing)
            return resized_frame
        # Frame is already Full HD or smaller
        resize_time = time.time() - resize_start
        if self.monitoring_collector:
            timing = self.monitoring_collector.get_timing_breakdown()
            timing['resize'] = resize_time
            self.monitoring_collector.update_timing_breakdown(timing)
        return frame

    def _save_frame_to_database_if_needed(self, frame):
        """Queues the current frame for database save if one hour has passed (non-blocking)"""
        current_time = time.time()

        if current_time - self.last_frame_save_time >= self.frame_save_interval:
            self.last_frame_save_time = current_time
            try:
                # Queue for background processing
                frame_copy = copy.deepcopy(frame)
                self.db_queue.put_nowait((frame_copy, 0.0, time.strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]))
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"✅ Hourly frame queued for database save at {timestamp}")
                return True
            except queue.Full:
                print("⚠️  Database queue full, skipping hourly frame save")
                return False
            except Exception as e:
                print(f"⚠️  Error queueing hourly frame save: {e}")
                return False

        return False

    def _process_detections(self, frame, detections, results, timestamp, timestamp_readable, detection_time: float):
        """Processes the detections with priority: MQTT first, then background tasks
        
        Args:
            frame: The video frame
            detections: List of detections
            results: YOLO results object
            timestamp: Timestamp string (generated BEFORE detection to avoid delay)
            timestamp_readable: Human-readable timestamp
            detection_time: Time taken for detection in seconds
        """
        for class_id, confidence, bbox in detections:
            class_name = self.detector.CLASS_NAMES.get(class_id, "Unknown")
            if confidence > self.config.confidence_threshold:
                print(f"✅ Processing {class_name} (Confidence: {confidence:.4f} > Threshold: {self.config.confidence_threshold})")
            else:
                print(f"❌ Skipping {class_name} (Confidence: {confidence:.4f} <= Threshold: {self.config.confidence_threshold})")
                continue
            
            # Check ignore zone
            if self.detector.is_in_ignore_zone(bbox, frame.shape,
                                             self.config.ignore_zone):
                print(f"⏭️  {class_name} in ignore zone, skipping")
                continue

            # Annotate frame
            annotated_frame = None
            for result in results:
                annotated_frame = result.plot()
                break

            if annotated_frame is None:
                continue

            # PRIORITY 1: Send MQTT message IMMEDIATELY (non-blocking, highest priority)
            # This ensures the detection is reported as fast as possible
            mqtt_start = time.time()
            self.mqtt_handler.publish_detection(class_name, confidence, timestamp)
            mqtt_time = time.time() - mqtt_start
            print(f'[{timestamp_readable}] 🚨 Detected: {class_name} (ID: {class_id}, Confidence: {confidence:.4f}) - MQTT sent')
            
            # Update monitoring with detection and MQTT timing
            if self.monitoring_collector:
                self.monitoring_collector.add_detection(
                    class_name, confidence, bbox, timestamp, detection_time
                )
                timing = self.monitoring_collector.get_timing_breakdown()
                timing['mqtt_publish'] = mqtt_time
                self.monitoring_collector.update_timing_breakdown(timing)

            # PRIORITY 2: Queue frame for background file saving (non-blocking)
            self._save_detection(annotated_frame, timestamp)

            # PRIORITY 3: Queue database save for background (non-blocking)
            try:
                # Make a copy of the frame for the background thread
                frame_copy = copy.deepcopy(annotated_frame)
                self.db_queue.put_nowait((frame_copy, confidence, timestamp))
            except queue.Full:
                print("⚠️  Database queue full, skipping DB save (non-critical)")
            except Exception as e:
                print(f"⚠️  Error queueing database save: {e}")

    def run(self):
        """Main loop for stream processing"""
        retry_delay = 5
        max_retry_delay = 60
        consecutive_failures = 0
        
        while True:
            print(f"🎥 Attempting to connect to RTSP stream: {self.config.rtsp_stream_url}")
            
            # Set OpenCV RTSP options for faster timeout and better compatibility
            # Use FFmpeg backend with low-latency RTSP options
            rtsp_url = self.config.rtsp_stream_url
            # Add FFmpeg options for low latency: drop old frames and use TCP for reliability
            if '?' not in rtsp_url:
                rtsp_url += '?rtsp_transport=tcp&buffer_size=1'
            else:
                rtsp_url += '&rtsp_transport=tcp&buffer_size=1'
            
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)  # 15 second timeout
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)  # 5 second read timeout (shorter for faster recovery)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer (1 frame) to prevent delay accumulation

            if not cap.isOpened():
                consecutive_failures += 1
                print(f"❌ Failed to open RTSP stream (attempt #{consecutive_failures})")
                print(f"   Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                
                # Exponential backoff: increase delay after each failure
                retry_delay = min(retry_delay * 1.5, max_retry_delay)
                continue

            print("✅ RTSP stream connection established successfully")
            consecutive_failures = 0
            retry_delay = 5  # Reset retry delay on success
            frame_read_failures = 0
            max_frame_failures = 10
            
            # Update monitoring: streaming started
            if self.monitoring_collector:
                self.monitoring_collector.set_streaming_status(True)

            # Process frames
            while cap.isOpened():
                # Start timing for performance monitoring
                frame_start_time = time.time()
                timing_breakdown = {
                    'frame_read': 0.0,
                    'resize': 0.0,
                    'detection': 0.0,
                    'mqtt_publish': 0.0,
                    'db_queue_wait': 0.0,
                    'file_queue_wait': 0.0,
                    'total': 0.0
                }
                
                # Dynamic frame skipping based on processing performance
                # Calculate how many frames to skip based on recent processing times
                avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
                if avg_processing_time > self.max_processing_time:
                    # Processing is too slow, skip more frames
                    max_frames_to_skip = min(int(avg_processing_time / self.max_processing_time) + 2, 10)
                    if max_frames_to_skip > 5:
                        print(f"⚠️  Slow processing detected (avg: {avg_processing_time:.2f}s), skipping up to {max_frames_to_skip} frames")
                else:
                    max_frames_to_skip = 3  # Normal: skip 3 frames to get latest
                
                # Time frame reading
                frame_read_start = time.time()
                ret, frame = None, None
                frames_skipped = 0
                
                # Skip buffered frames to get the most recent one
                for _ in range(max_frames_to_skip):
                    temp_ret, temp_frame = cap.read()
                    if temp_ret:
                        ret, frame = temp_ret, temp_frame
                        frames_skipped += 1
                    else:
                        break
                
                frame_read_time = time.time() - frame_read_start
                timing_breakdown['frame_read'] = frame_read_time
                
                if not ret:
                    frame_read_failures += 1
                    print(f"⚠️  Failed to read frame ({frame_read_failures}/{max_frame_failures})")
                    
                    if frame_read_failures >= max_frame_failures:
                        print("❌ Too many frame read failures. Reconnecting...")
                        if self.monitoring_collector:
                            self.monitoring_collector.set_streaming_status(False)
                        break
                    
                    time.sleep(0.5)
                    continue
                
                # Reset failure counter on successful read
                frame_read_failures = 0
                
                # Update monitoring: frames skipped
                if frames_skipped > 0 and self.monitoring_collector:
                    self.monitoring_collector.increment_frames_skipped(frames_skipped)
                
                # Generate timestamp BEFORE processing to capture actual detection time
                # This prevents delay accumulation from slow processing
                timestamp = time.strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]
                timestamp_readable = time.strftime('%Y-%m-%d %H:%M:%S')

                # Reduce frame resolution from 4K to Full HD
                frame = self._resize_frame_to_fullhd(frame)
                
                # Update frame in monitoring (every 5th frame to reduce overhead)
                if self.monitoring_collector and self._total_frames_processed % 5 == 0:
                    self.monitoring_collector.update_frame(frame, time.time())

                # Save frame to database every hour (non-blocking, in background)
                self._save_frame_to_database_if_needed(frame)

                # Object detection (this is the main blocking operation)
                detection_start = time.time()
                detections, results = self.detector.detect_objects(frame)
                detection_time = time.time() - detection_start
                timing_breakdown['detection'] = detection_time

                # Debug: Print all detections before filtering
                if detections:
                    print(f"🔍 Found {len(detections)} detection(s) before filtering (detection took {detection_time:.3f}s):")
                    for class_id, confidence, bbox in detections:
                        class_name = self.detector.CLASS_NAMES.get(class_id, "Unknown")
                        print(f"   - {class_name} (ID: {class_id}, Confidence: {confidence:.4f}, Threshold: {self.config.confidence_threshold})")

                # Process detections (pass timestamp from before detection)
                # MQTT is sent immediately, DB and file save happen in background
                if detections:
                    self._process_detections(frame, detections, results, timestamp, timestamp_readable, detection_time)
                
                # Explicitly free YOLO results to prevent memory leaks
                del results
                del detections
                
                # Track processing time for dynamic frame skipping
                total_processing_time = time.time() - frame_start_time
                timing_breakdown['total'] = total_processing_time
                
                # Increment frame counter
                self._total_frames_processed += 1
                
                # Update monitoring with all timing information
                if self.monitoring_collector:
                    self.monitoring_collector.update_timing_breakdown(timing_breakdown)
                    self.monitoring_collector.update_processing_time(total_processing_time)
                    # Update queue status
                    self.monitoring_collector.update_queue_status(
                        self.db_queue.qsize(),
                        0.0,  # Will be updated by workers
                        self.file_queue.qsize(),
                        0.0   # Will be updated by workers
                    )
                
                self.processing_times.append(total_processing_time)
                if len(self.processing_times) > self.max_processing_times:
                    self.processing_times.pop(0)  # Keep only last N times
                
                # Warn if processing is getting slow
                if total_processing_time > 2.0:
                    print(f"⚠️  Slow frame processing: {total_processing_time:.2f}s (target: <{self.max_processing_time:.2f}s)")

                # Note: cv2.waitKey() removed - not needed in headless Docker container
                # Container can be stopped with: docker stop katzenschreck

            cap.release()
            if self.monitoring_collector:
                self.monitoring_collector.set_streaming_status(False)
            print("🔄 Stream disconnected. Attempting to reconnect...")

        print(f'Frames with detected objects are saved in folder '
              f'"{self.output_dir}".')
