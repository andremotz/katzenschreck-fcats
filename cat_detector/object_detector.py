"""Object detection using YOLO for cat detection"""

import os
from typing import Optional, List, Tuple
from ultralytics import YOLO
from .hardware_detector import HardwareDetector


class ObjectDetector:
    """YOLO object detection class with automatic hardware detection"""

    CLASS_NAMES = {0: 'Person', 15: 'Cat'}
    TARGET_CLASS_IDS = [0, 15]  # Person and Cat

    def __init__(self, model_path: Optional[str] = None, hardware_type: Optional[str] = None):
        # Detect hardware type for optimization (reused for model selection and inference params)
        hardware_detector = HardwareDetector(forced_type=hardware_type)
        self.is_jetson = hardware_detector.is_jetson
        
        # Auto-detect optimal model if not specified
        if model_path is None:
            model_path, requirements_file = hardware_detector.get_optimal_model()
            print(f"🤖 Auto-detected optimal model: {model_path}")
            print(f"📋 Using requirements: {requirements_file}")
        
        # Resolve relative paths (e.g., runs/train15/weights/best.pt)
        if not os.path.isabs(model_path) and not os.path.exists(model_path):
            # Try relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            absolute_path = os.path.join(project_root, model_path)
            if os.path.exists(absolute_path):
                model_path = absolute_path
        
        self.model = YOLO(model_path)
        
        # Set memory-efficient parameters for Jetson
        if self.is_jetson:
            print("🔧 Optimizing YOLO for Jetson (reduced memory usage)")
            # Use smaller image size and FP16 for Jetson to reduce memory usage
            self.inference_params = {
                'imgsz': 640,  # Reduced from default to save memory
                'half': True,   # Use FP16 precision on Jetson
                'device': 0,   # Use GPU
                'verbose': False
            }
        else:
            self.inference_params = {
                'imgsz': 1280,  # Standard size for other hardware
                'verbose': False
            }

    def detect_objects(self, frame) -> Tuple[List[Tuple[int, float, List[float]]],
                                            object]:
        """Detects objects in frame and returns relevant detections"""
        # Use memory-efficient parameters, especially for Jetson
        results = self.model(frame, **self.inference_params)
        detections = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls.item())

                # Detect both persons and cats
                if class_id in self.TARGET_CLASS_IDS:
                    confidence = box.conf.item()
                    bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    detections.append((class_id, confidence, bbox))

        return detections, results

    def is_in_ignore_zone(self, bbox: List[float], frame_shape: Tuple[int, int],
                          ignore_zone: Optional[List[float]]) -> bool:
        """Checks if the bounding box is in the ignore zone"""
        if not ignore_zone:
            return False

        x1, y1, x2, y2 = bbox
        frame_h, frame_w = frame_shape[:2]

        # Box coordinates as percentage values
        box_coords = self._get_box_percentage_coords(x1, y1, x2, y2, frame_w, frame_h)

        # Ignore zone coordinates
        iz_xmin, iz_ymin, iz_xmax, iz_ymax = ignore_zone

        # Check if box overlaps with ignore zone
        return self._check_box_overlap(box_coords, (iz_xmin, iz_ymin, iz_xmax, iz_ymax))

    def _get_box_percentage_coords(self, x1, y1, x2, y2, frame_w, frame_h):
        """Convert box coordinates to percentage values"""
        return {
            'xmin': x1 / frame_w,
            'ymin': y1 / frame_h,
            'xmax': x2 / frame_w,
            'ymax': y2 / frame_h
        }

    def _check_box_overlap(self, box_coords, ignore_zone):
        """Check if box overlaps with ignore zone"""
        iz_xmin, iz_ymin, iz_xmax, iz_ymax = ignore_zone
        return not (box_coords['xmax'] < iz_xmin or box_coords['xmin'] > iz_xmax or
                   box_coords['ymax'] < iz_ymin or box_coords['ymin'] > iz_ymax)
