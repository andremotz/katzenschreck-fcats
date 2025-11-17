"""Video stream processing for the cat deterrent system"""

import os
import time
import cv2
import sys

# Add the parent directory to the Python path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_detector.config import Config
from cat_detector.object_detector import ObjectDetector
from cat_detector.mqtt_handler import MQTTHandler
from cat_detector.database_handler import DatabaseHandler
from cat_detector.results_cleanup import cleanup_results_folder


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

        # Create output directory
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _save_detection(self, annotated_frame, timestamp: str):
        """Saves the detected frame"""
        cleanup_results_folder(self.output_dir, self.config.usage_threshold)
        output_file = f'{self.output_dir}/frame_{timestamp}.jpg'
        cv2.imwrite(output_file, annotated_frame)

    def _resize_frame_to_fullhd(self, frame):
        """Reduces frame resolution from 4K to Full HD (1920x1080)"""
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
            return resized_frame
        # Frame is already Full HD or smaller
        return frame

    def _save_frame_to_database_if_needed(self, frame):
        """Saves the current frame to database if one hour has passed"""
        current_time = time.time()

        if current_time - self.last_frame_save_time >= self.frame_save_interval:
            self.last_frame_save_time = current_time
            success = self.db_handler.save_frame_to_database(frame)
            if success:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"Frame saved to database at {timestamp}")
            return success

        return False

    def _process_detections(self, frame, detections, results):
        """Processes the detections"""
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

            # Generate timestamp
            timestamp = time.strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3]
            timestamp_readable = time.strftime('%Y-%m-%d %H:%M:%S')

            # Save frame
            self._save_detection(annotated_frame, timestamp)

            # Save detection image to database
            success = self.db_handler.save_frame_to_database(
                annotated_frame, confidence)
            if success:
                print(f"Detection image saved to database "
                      f"(Confidence: {confidence:.2f})")
            else:
                print("Error saving detection image to database")

            # Output information with timestamp and confidence
            print(f'[{timestamp_readable}] Detected: {class_name} (ID: {class_id}, Confidence: {confidence:.4f})')

            # Send MQTT message
            self.mqtt_handler.publish_detection(class_name, confidence,
                                               timestamp)

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
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # Small buffer (2 frames) to balance latency and stability

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

            # Process frames
            while cap.isOpened():
                # Skip old frames in buffer to always get the latest frame
                # This prevents delay accumulation when processing is slower than stream FPS
                # Read frames quickly until we get the most recent one (max 2 attempts to avoid stream issues)
                ret, frame = cap.read()
                if ret:
                    # Try to get a newer frame if available (only once to avoid overloading stream)
                    # This ensures we process a relatively recent frame without breaking the connection
                    temp_ret, temp_frame = cap.read()
                    if temp_ret:
                        # A newer frame was available, use that instead
                        ret, frame = temp_ret, temp_frame
                
                if not ret:
                    frame_read_failures += 1
                    print(f"⚠️  Failed to read frame ({frame_read_failures}/{max_frame_failures})")
                    
                    if frame_read_failures >= max_frame_failures:
                        print("❌ Too many frame read failures. Reconnecting...")
                        break
                    
                    time.sleep(0.5)
                    continue
                
                # Reset failure counter on successful read
                frame_read_failures = 0

                # Reduce frame resolution from 4K to Full HD
                frame = self._resize_frame_to_fullhd(frame)

                # Save frame to database every hour
                self._save_frame_to_database_if_needed(frame)

                # Object detection
                detections, results = self.detector.detect_objects(frame)

                # Debug: Print all detections before filtering
                if detections:
                    print(f"🔍 Found {len(detections)} detection(s) before filtering:")
                    for class_id, confidence, bbox in detections:
                        class_name = self.detector.CLASS_NAMES.get(class_id, "Unknown")
                        print(f"   - {class_name} (ID: {class_id}, Confidence: {confidence:.4f}, Threshold: {self.config.confidence_threshold})")

                # Process detections
                if detections:
                    self._process_detections(frame, detections, results)

                # Note: cv2.waitKey() removed - not needed in headless Docker container
                # Container can be stopped with: docker stop katzenschreck

            cap.release()
            print("🔄 Stream disconnected. Attempting to reconnect...")

        print(f'Frames with detected objects are saved in folder '
              f'"{self.output_dir}".')
