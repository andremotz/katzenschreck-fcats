"""Threaded RTSP stream reader with buffer cleansing to prevent frame drift"""

import cv2
import threading
import time
import os
from typing import Optional, Tuple


class RTSPStreamReader:
    """Threaded RTSP stream reader that continuously reads frames to prevent buffering
    
    This class uses a separate thread to continuously read frames from the RTSP stream,
    keeping only the latest frame available. This prevents OpenCV's internal buffer
    from accumulating old frames during slow processing.
    """

    def __init__(self, rtsp_url: str, transport: str = 'udp', low_delay: bool = True):
        """Initialize the RTSP stream reader
        
        Args:
            rtsp_url: RTSP stream URL
            transport: Transport protocol ('udp' or 'tcp'), default 'udp'
            low_delay: Enable low-delay mode, default True
        """
        self.rtsp_url = rtsp_url
        self.transport = transport.lower()
        self.low_delay = low_delay
        
        # Thread-safe frame storage
        self._lock = threading.Lock()
        self._frame: Optional[Tuple[bool, any]] = None  # (success, frame)
        self._frame_timestamp: float = 0.0
        self._frame_number: int = 0
        
        # Control flags
        self._stopped = False
        self._connected = False
        self._cap: Optional[cv2.VideoCapture] = None
        
        # Statistics
        self._frames_read = 0
        self._frames_dropped = 0
        self._last_error: Optional[str] = None
        
        # Start the reader thread
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _build_rtsp_url(self) -> str:
        """Build RTSP URL with FFmpeg options for low latency"""
        url = self.rtsp_url
        
        # Build query parameters
        params = []
        
        # Transport protocol
        if self.transport == 'udp':
            params.append('rtsp_transport=udp')
        else:
            params.append('rtsp_transport=tcp')
        
        # Low delay mode
        if self.low_delay:
            params.append('low_delay=1')
        
        # Buffer size (minimal)
        params.append('buffer_size=1')
        
        # Timeout (5 seconds in microseconds)
        params.append('stimeout=5000000')
        
        # Combine parameters
        param_string = '&'.join(params)
        
        if '?' in url:
            return f"{url}&{param_string}"
        else:
            return f"{url}?{param_string}"

    def _read_loop(self):
        """Main loop running in separate thread - continuously reads frames"""
        retry_delay = 2
        max_retry_delay = 30
        
        while not self._stopped:
            try:
                # Build URL with FFmpeg options
                rtsp_url_with_options = self._build_rtsp_url()
                
                # Set FFmpeg environment variables for low latency
                if self.transport == 'udp':
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|low_delay;1"
                else:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|low_delay;1"
                
                # Open video capture
                self._cap = cv2.VideoCapture(rtsp_url_with_options, cv2.CAP_FFMPEG)
                
                # Set capture properties for low latency
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self._cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                self._cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
                
                if not self._cap.isOpened():
                    self._last_error = "Failed to open RTSP stream"
                    print(f"❌ RTSP Reader: {self._last_error}")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, max_retry_delay)
                    continue
                
                print(f"✅ RTSP Reader: Connected to stream (transport: {self.transport})")
                self._connected = True
                retry_delay = 2  # Reset retry delay on success
                
                # Continuously read frames
                consecutive_failures = 0
                max_failures = 10
                
                while not self._stopped and self._cap.isOpened():
                    # Use grab() first - it's faster (no decoding)
                    if not self._cap.grab():
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            print("❌ RTSP Reader: Too many grab failures, reconnecting...")
                            break
                        time.sleep(0.1)
                        continue
                    
                    # Retrieve the frame (decode)
                    ret, frame = self._cap.retrieve()
                    
                    if ret and frame is not None:
                        # Update frame in thread-safe manner
                        with self._lock:
                            # Count dropped frames (if we're overwriting an unread frame)
                            if self._frame is not None and self._frame[0]:
                                self._frames_dropped += 1
                            
                            self._frame = (True, frame.copy())
                            self._frame_timestamp = time.time()
                            self._frame_number += 1
                            self._frames_read += 1
                        
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures:
                            print("❌ RTSP Reader: Too many read failures, reconnecting...")
                            break
                
                # Clean up
                if self._cap:
                    self._cap.release()
                    self._cap = None
                
                self._connected = False
                print("🔄 RTSP Reader: Disconnected, reconnecting...")
                
            except Exception as e:
                self._last_error = str(e)
                print(f"⚠️  RTSP Reader error: {e}")
                self._connected = False
                if self._cap:
                    try:
                        self._cap.release()
                    except Exception:
                        pass
                    self._cap = None
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, max_retry_delay)

    def get_latest_frame(self) -> Optional[Tuple[bool, any, float, int]]:
        """Get the latest frame from the stream
        
        Returns:
            Tuple of (success, frame, timestamp, frame_number) or None if no frame available
            - success: bool indicating if frame was successfully read
            - frame: numpy array with the frame (or None if failed)
            - timestamp: timestamp when frame was captured
            - frame_number: sequential frame number
        """
        with self._lock:
            if self._frame is None:
                return None
            
            success, frame = self._frame
            if success:
                # Return a copy to prevent race conditions
                return (True, frame.copy(), self._frame_timestamp, self._frame_number)
            else:
                return (False, None, self._frame_timestamp, self._frame_number)

    def get_frame_age(self) -> float:
        """Get the age of the current frame in seconds
        
        Returns:
            Age in seconds, or -1 if no frame available
        """
        with self._lock:
            if self._frame is None or self._frame_timestamp == 0:
                return -1.0
            return time.time() - self._frame_timestamp

    def is_connected(self) -> bool:
        """Check if the stream is currently connected"""
        return self._connected

    def get_statistics(self) -> dict:
        """Get reader statistics
        
        Returns:
            Dictionary with statistics:
            - frames_read: Total frames read
            - frames_dropped: Frames dropped due to buffer overflow
            - frame_number: Current frame number
            - connected: Connection status
            - last_error: Last error message (if any)
        """
        with self._lock:
            return {
                'frames_read': self._frames_read,
                'frames_dropped': self._frames_dropped,
                'frame_number': self._frame_number,
                'connected': self._connected,
                'last_error': self._last_error
            }

    def stop(self):
        """Stop the reader thread and release resources"""
        self._stopped = True
        if self._thread.is_alive():
            self._thread.join(timeout=5.0)
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        print("🛑 RTSP Reader: Stopped")

