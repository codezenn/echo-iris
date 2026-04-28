"""
iris_detector.py - IMX500 Object Detection for Echo IRIS
Runs MobileNet SSD on the Sony IMX500 AI Camera continuously.
Provides get_detection_summary() for the voice pipeline.

Usage:
    from iris_detector import IrisDetector
    detector = IrisDetector(preview_width=960, preview_height=540, preview_x=960, preview_y=0)
    detector.start()
    summary = detector.get_detection_summary()
    detector.stop()
"""

import threading
import time
import sys
from collections import Counter

import cv2
import numpy as np

from picamera2 import MappedArray, Picamera2, Preview
from picamera2.devices import IMX500
from picamera2.devices.imx500 import (NetworkIntrinsics,
                                      postprocess_nanodet_detection)

# Default model path (MobileNet SSD, shipped with imx500-all)
DEFAULT_MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"

# Detection defaults
DEFAULT_THRESHOLD = 0.55
DEFAULT_IOU = 0.65
DEFAULT_MAX_DETECTIONS = 10

# Preview window defaults (right half of 1920x1080 monitor)
DEFAULT_PREVIEW_WIDTH = 960
DEFAULT_PREVIEW_HEIGHT = 720
DEFAULT_PREVIEW_X = 960
DEFAULT_PREVIEW_Y = 0


class Detection:
    def __init__(self, coords, category, conf, metadata, imx500_dev, picam2_dev):
        self.category = category
        self.conf = conf
        self.box = imx500_dev.convert_inference_coords(coords, metadata, picam2_dev)


class IrisDetector:
    def __init__(self, model_path=DEFAULT_MODEL, threshold=DEFAULT_THRESHOLD,
                 iou=DEFAULT_IOU, max_detections=DEFAULT_MAX_DETECTIONS,
                 preview_width=DEFAULT_PREVIEW_WIDTH, preview_height=DEFAULT_PREVIEW_HEIGHT,
                 preview_x=DEFAULT_PREVIEW_X, preview_y=DEFAULT_PREVIEW_Y):
        self.model_path = model_path
        self.threshold = threshold
        self.iou = iou
        self.max_detections = max_detections
        self.preview_width = preview_width
        self.preview_height = preview_height
        self.preview_x = preview_x
        self.preview_y = preview_y

        self._detections = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._picam2 = None
        self._imx500 = None
        self._intrinsics = None
        self._labels = None
        self._initialized = False

    def start(self):
        """Initialize IMX500 and start continuous detection with preview window."""
        if self._running:
            return

        print("[DETECTOR] Initializing IMX500...")

        # IMX500 must be created before Picamera2
        self._imx500 = IMX500(self.model_path)
        self._intrinsics = self._imx500.network_intrinsics
        if not self._intrinsics:
            self._intrinsics = NetworkIntrinsics()
            self._intrinsics.task = "object detection"

        # Load labels
        if self._intrinsics.labels is None:
            label_paths = [
                "assets/coco_labels.txt",
                "/home/penrose/Desktop/AI Cam/assets/coco_labels.txt",
                "/usr/share/imx500-models/coco_labels.txt",
            ]
            for lp in label_paths:
                try:
                    with open(lp, "r") as f:
                        self._intrinsics.labels = f.read().splitlines()
                    print(f"[DETECTOR] Loaded labels from {lp}")
                    break
                except FileNotFoundError:
                    continue

        self._intrinsics.update_with_defaults()

        # Build clean label list
        labels = self._intrinsics.labels
        if self._intrinsics.ignore_dash_labels and labels:
            labels = [l for l in labels if l and l != "-"]
        self._labels = labels

        # Create and configure Picamera2
        self._picam2 = Picamera2(self._imx500.camera_num)
        config = self._picam2.create_preview_configuration(
            controls={"FrameRate": self._intrinsics.inference_rate},
            buffer_count=12
        )

        # Show firmware upload progress
        self._imx500.show_network_fw_progress_bar()

        # Start preview window at custom size and position
        self._picam2.start_preview(
            Preview.QTGL,
            x=self.preview_x,
            y=self.preview_y,
            width=self.preview_width,
            height=self.preview_height,
        )

        # Configure and start camera
        self._picam2.configure(config)
        self._picam2.start()

        if self._intrinsics.preserve_aspect_ratio:
            self._imx500.set_auto_aspect_ratio()

        # Register the overlay drawing callback
        self._picam2.pre_callback = self._draw_detections

        self._initialized = True
        self._running = True

        # Start detection loop in background thread
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        print(f"[DETECTOR] Running. Preview: {self.preview_width}x{self.preview_height} at ({self.preview_x}, {self.preview_y})")

    def stop(self):
        """Stop detection and release camera."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._picam2:
            try:
                self._picam2.stop()
                self._picam2.stop_preview()
                self._picam2.close()
            except Exception:
                pass
            self._picam2 = None
        self._initialized = False
        print("[DETECTOR] Stopped.")

    def _detection_loop(self):
        """Continuously parse detections from IMX500 metadata."""
        while self._running:
            try:
                metadata = self._picam2.capture_metadata()
                detections = self._parse_detections(metadata)
                with self._lock:
                    self._detections = detections
            except Exception as e:
                print(f"[DETECTOR] Error: {e}")
                time.sleep(0.1)

    def _parse_detections(self, metadata):
        """Parse output tensor into Detection objects."""
        np_outputs = self._imx500.get_outputs(metadata, add_batch=True)
        input_w, input_h = self._imx500.get_input_size()
        if np_outputs is None:
            with self._lock:
                return list(self._detections)

        bbox_normalization = self._intrinsics.bbox_normalization
        bbox_order = self._intrinsics.bbox_order

        if self._intrinsics.postprocess == "nanodet":
            boxes, scores, classes = postprocess_nanodet_detection(
                outputs=np_outputs[0], conf=self.threshold,
                iou_thres=self.iou, max_out_dets=self.max_detections
            )[0]
            from picamera2.devices.imx500.postprocess import scale_boxes
            boxes = scale_boxes(boxes, 1, 1, input_h, input_w, False, False)
        else:
            boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]
            if bbox_normalization:
                boxes = boxes / input_h
            if bbox_order == "xy":
                boxes = boxes[:, [1, 0, 3, 2]]
            boxes = np.array_split(boxes, 4, axis=1)
            boxes = zip(*boxes)

        detections = [
            Detection(box, category, score, metadata,
                      self._imx500, self._picam2)
            for box, score, category in zip(boxes, scores, classes)
            if score > self.threshold
        ]
        return detections

    def _draw_detections(self, request, stream="main"):
        """Overlay bounding boxes and labels on the preview."""
        with self._lock:
            detections = list(self._detections)
        if not detections or not self._labels:
            return

        with MappedArray(request, stream) as m:
            for detection in detections:
                x, y, w, h = detection.box
                label_idx = int(detection.category)
                if label_idx >= len(self._labels):
                    continue
                label = f"{self._labels[label_idx]} ({detection.conf:.2f})"

                (text_width, text_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )
                text_x = x + 5
                text_y = y + 15

                # Semi-transparent white background for label
                overlay = m.array.copy()
                cv2.rectangle(overlay,
                              (text_x, text_y - text_height),
                              (text_x + text_width, text_y + baseline),
                              (255, 255, 255), cv2.FILLED)
                cv2.addWeighted(overlay, 0.30, m.array, 0.70, 0, m.array)

                # Label text
                cv2.putText(m.array, label, (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                # Bounding box
                cv2.rectangle(m.array, (x, y), (x + w, y + h),
                              (0, 255, 0, 0), thickness=2)

    def get_detections(self):
        """Get current detection list (thread-safe)."""
        with self._lock:
            return list(self._detections)

    def get_detection_summary(self):
        """Generate a spoken sentence describing what IRIS sees."""
        with self._lock:
            detections = list(self._detections)

        if not detections or not self._labels:
            return "I don't see anything right now."

        counts = Counter()
        for d in detections:
            label_idx = int(d.category)
            if label_idx < len(self._labels):
                counts[self._labels[label_idx]] += 1

        if not counts:
            return "I don't see anything right now."

        parts = []
        number_words = {
            1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"
        }
        irregular_plurals = {
            "person": "people",
            "child": "children",
            "mouse": "mice",
            "foot": "feet",
            "tooth": "teeth",
        }

        for label, count in counts.most_common():
            num = number_words.get(count, str(count))
            if count > 1:
                if label.lower() in irregular_plurals:
                    plural = irregular_plurals[label.lower()]
                elif label.endswith("s") or label.endswith("sh") or label.endswith("ch"):
                    plural = label + "es"
                elif label.endswith("y"):
                    plural = label[:-1] + "ies"
                else:
                    plural = label + "s"
                parts.append(f"{num} {plural}")
            else:
                article = "an" if label[0].lower() in "aeiou" else "a"
                parts.append(f"{article} {label}")

        if len(parts) == 1:
            object_list = parts[0]
        elif len(parts) == 2:
            object_list = f"{parts[0]} and {parts[1]}"
        else:
            object_list = ", ".join(parts[:-1]) + f", and {parts[-1]}"

        return f"I can see {object_list}."

    def is_running(self):
        """Check if detector is active."""
        return self._running and self._initialized
