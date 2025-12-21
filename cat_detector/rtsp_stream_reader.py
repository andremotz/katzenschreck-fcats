"""Threaded RTSP stream reader with buffer cleansing to prevent frame drift"""

import cv2
import threading
import time
import os
from typing import Optional, Tuple


class RTSPStreamReader:
    """RTSP stream reader with two modes: continuous (threaded) or reconnect_per_frame
    
    - continuous: Uses a separate thread to continuously read frames, keeping only the latest
    - reconnect_per_frame: Reconnects before each frame to guarantee fresh frames (no buffer)
    """

    def __init__(self, rtsp_url: str, transport: str = 'udp', low_delay: bool = True, 
                 mode: str = 'continuous'):
        """Initialize the RTSP stream reader
        
        Args:
            rtsp_url: RTSP stream URL
            transport: Transport protocol ('udp' or 'tcp'), default 'udp'
            low_delay: Enable low-delay mode, default True
            mode: Connection mode ('continuous' or 'reconnect_per_frame'), default 'continuous'
        """
        self.rtsp_url = rtsp_url
        self.transport = transport.lower()
        self.low_delay = low_delay
        self.mode = mode.lower()
        
        if self.mode not in ['continuous', 'reconnect_per_frame']:
            self.mode = 'continuous'
        
        # Thread-safe frame storage (for continuous mode)
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
        self._reconnection_times = []  # Track reconnection times for reconnect_per_frame mode
        self._last_reconnection_time = 0.0
        
        # Start the reader thread only in continuous mode
        if self.mode == 'continuous':
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
        else:
            self._thread = None
            print(f"✅ RTSP Reader: Initialized in reconnect_per_frame mode")

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

    def get_fresh_frame(self) -> Optional[Tuple[bool, any, float, int]]:
        """Get a fresh frame by reconnecting to the stream (reconnect_per_frame mode only)
        
        Opens the stream, reads exactly one frame, then closes it immediately.
        This guarantees the frame is fresh with no buffer.
        
        Returns:
            Tuple of (success, frame, timestamp, frame_number) or None if failed
        """
        if self.mode != 'reconnect_per_frame':
            raise RuntimeError("get_fresh_frame() can only be used in reconnect_per_frame mode")
        
        reconnection_start = time.time()
        
        try:
            # Build URL with FFmpeg options
            rtsp_url_with_options = self._build_rtsp_url()
            
            # Set FFmpeg environment variables for low latency
            if self.transport == 'udp':
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|low_delay;1"
            else:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|low_delay;1"
            
            # Open video capture with minimal timeouts for fast reconnection
            cap = cv2.VideoCapture(rtsp_url_with_options, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000)  # 2 seconds for fast reconnection
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000)  # 2 seconds read timeout
            
            if not cap.isOpened():
                self._last_error = "Failed to open RTSP stream for fresh frame"
                return None
            
            # Read exactly one frame (the first one is always fresh after reconnect)
            ret, frame = cap.read()
            
            # Close immediately after reading
            cap.release()
            
            reconnection_time = time.time() - reconnection_start
            self._last_reconnection_time = reconnection_time
            self._reconnection_times.append(reconnection_time)
            if len(self._reconnection_times) > 100:
                self._reconnection_times.pop(0)  # Keep last 100
            
            if ret and frame is not None:
                self._frames_read += 1
                self._frame_number += 1
                frame_timestamp = time.time()
                
                # Warn if reconnection is slow
                if reconnection_time > 1.0:
                    print(f"⚠️  Slow reconnection: {reconnection_time:.2f}s")
                
                return (True, frame, frame_timestamp, self._frame_number)
            else:
                self._last_error = "Failed to read frame after reconnection"
                return None
                
        except Exception as e:
            self._last_error = str(e)
            print(f"⚠️  Error getting fresh frame: {e}")
            return None

    def get_latest_frame(self) -> Optional[Tuple[bool, any, float, int]]:
        """Get the latest frame from the stream (continuous mode only)
        
        Returns:
            Tuple of (success, frame, timestamp, frame_number) or None if no frame available
            - success: bool indicating if frame was successfully read
            - frame: numpy array with the frame (or None if failed)
            - timestamp: timestamp when frame was captured
            - frame_number: sequential frame number
        """
        if self.mode != 'continuous':
            raise RuntimeError("get_latest_frame() can only be used in continuous mode. Use get_fresh_frame() for reconnect_per_frame mode")
        
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
            - frames_dropped: Frames dropped due to buffer overflow (continuous mode only)
            - frame_number: Current frame number
            - connected: Connection status (continuous mode only)
            - last_error: Last error message (if any)
            - mode: Current connection mode
            - last_reconnection_time: Last reconnection time in seconds (reconnect_per_frame mode)
            - avg_reconnection_time: Average reconnection time (reconnect_per_frame mode)
        """
        stats = {
            'frames_read': self._frames_read,
            'frame_number': self._frame_number,
            'last_error': self._last_error,
            'mode': self.mode
        }
        
        if self.mode == 'continuous':
            with self._lock:
                stats.update({
                    'frames_dropped': self._frames_dropped,
                    'connected': self._connected
                })
        else:  # reconnect_per_frame mode
            stats.update({
                'last_reconnection_time': self._last_reconnection_time,
                'avg_reconnection_time': (sum(self._reconnection_times) / len(self._reconnection_times) 
                                         if self._reconnection_times else 0.0)
            })
        
        return stats

    def stop(self):
        """Stop the reader thread and release resources"""
        self._stopped = True
        if self.mode == 'continuous' and self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        print("🛑 RTSP Reader: Stopped")

