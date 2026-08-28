"""Step 4 of 4: same walk-toward-the-target loop as 3_approach.py, but
with Ultralytics/YOLO swapped out for a model you trained or downloaded
yourself — typically a TensorFlow Lite model, since that's the common
export target for anything running on a Pi/Jetson-class board, but the
loop below doesn't care what framework `detect()` uses internally.

    1_see.py          look, and print everything found
    2_count.py        count just one kind of thing
    3_approach.py     walk toward the closest match (Ultralytics/YOLO)
    4_custom_model.py <- you are here: same thing, with YOUR model

Everything below `detect()` is unchanged from 3_approach.py — the
approach loop only ever talks to `detect()`'s return value (a list of
Detection), never to any model-specific API. That boundary is the
whole point of this file: swap what's above the line, keep everything
below it.

The reference detect() here loads a TFLite model with the classic SSD
MobileNet output layout (boxes/classes/scores/count — what you get from
the TF Object Detection API, TF Hub's ssd_mobilenet_v1, or the Coral/TFLite
"object detection" sample most students start from). If your model's
export is shaped differently, adjust detect() to match — open it in
https://netron.app if you're not sure what its inputs/outputs look like,
or check whatever training pipeline produced it.

Needs OpenCV and NumPy (pip install -e '.[all]', same as the other ai/
examples) PLUS whatever your model needs to run — tflite-runtime or
tensorflow for a .tflite model, onnxruntime for .onnx, etc. That's on
you to install; see the README's "Bring your own model" note.

Usage:
    python3 examples/ai/4_custom_model.py [host]

    Stops on its own once it arrives; Ctrl+C to stop early.
"""
import os
import sys
import time
from typing import List, NamedTuple

import cv2
import numpy as np

from shepherd_sdk import Shepherd

# --- Customization point: everything from here down to detect()'s closing
# brace is what you replace with your own model. The approach loop past
# that point only ever sees Detection objects, so nothing below needs to
# change no matter what framework you're using.

MODEL_PATH = "model.tflite"    # drop your exported model next to this script
LABELS_PATH = "labels.txt"     # one class name per line, in your model's output order
INPUT_SIZE = (300, 300)        # (width, height) your model expects — check its docs/export config
TARGET = "person"              # any class name that appears in LABELS_PATH
MIN_CONFIDENCE = 0.5           # drop detections the model itself isn't confident about


class Detection(NamedTuple):
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float  # all four in original-frame pixel coordinates, same as Ultralytics' box.xyxy


def _load_interpreter(model_path: str):
    # tflite-runtime is the lightweight, TFLite-only package most
    # tutorials (and Raspberry Pi/Coral guides) point students at; a
    # full tensorflow install works too (some students will already have
    # it) and exposes the identical Interpreter API under tf.lite. Try
    # the small one first, fall back to the big one.
    try:
        from tflite_runtime.interpreter import Interpreter
    except ImportError:
        from tensorflow.lite import Interpreter
    interpreter = Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter


def _load_labels(labels_path: str) -> List[str]:
    with open(labels_path) as f:
        return [line.strip() for line in f if line.strip()]


def detect(frame, interpreter, labels: List[str]) -> List[Detection]:
    """Run one model pass over `frame` (a BGR OpenCV image) and return
    every detection above MIN_CONFIDENCE, in original-frame pixel
    coordinates. This is the function to rewrite for a differently-shaped
    model — everything else in this file stays the same."""
    frame_height, frame_width = frame.shape[:2]
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    resized = cv2.resize(frame, INPUT_SIZE)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    if input_details[0]["dtype"] == np.float32:
        # Float SSD MobileNet exports expect input scaled to roughly
        # [-1, 1]; quantized (uint8) ones expect raw 0-255 instead. If
        # your model was exported/trained with different preprocessing,
        # this is the line to change.
        input_data = (rgb.astype(np.float32) - 127.5) / 127.5
    else:
        input_data = rgb.astype(np.uint8)
    input_data = np.expand_dims(input_data, axis=0)

    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    # Classic SSD MobileNet TFLite output order: boxes, classes,
    # scores, count. Swap these indices if your model's outputs come
    # back in a different order (Netron will show you).
    boxes = interpreter.get_tensor(output_details[0]["index"])[0]     # [N, 4] as ymin,xmin,ymax,xmax (0..1)
    classes = interpreter.get_tensor(output_details[1]["index"])[0]   # [N] label indices
    scores = interpreter.get_tensor(output_details[2]["index"])[0]    # [N] confidences

    detections = []
    for box, cls, score in zip(boxes, classes, scores):
        if score < MIN_CONFIDENCE:
            continue
        label_idx = int(cls)
        if label_idx < 0 or label_idx >= len(labels):
            continue
        ymin, xmin, ymax, xmax = box
        detections.append(Detection(
            label=labels[label_idx],
            confidence=float(score),
            x1=xmin * frame_width, y1=ymin * frame_height,
            x2=xmax * frame_width, y2=ymax * frame_height,
        ))
    return detections


# --- End customization point. Everything below is identical in shape to
# 3_approach.py — it only depends on Detection, not on TFLite/Ultralytics/
# anything else.

FORWARD_SPEED = 0.3    # m/s, while approaching
TURN_SPEED = 1.0        # rad/s, at most, while centering on TARGET
CLOSE_ENOUGH = 0.5      # stop walking forward once TARGET's box fills
                        # this fraction of the frame's height


def box_area(det: Detection) -> float:
    return (det.x2 - det.x1) * (det.y2 - det.y1)


def main() -> None:
    for path in (MODEL_PATH, LABELS_PATH):
        if not os.path.exists(path):
            sys.exit(
                f"'{path}' not found. Export your model to {MODEL_PATH} and its "
                f"class names (one per line, in output order) to {LABELS_PATH} — "
                f"or point MODEL_PATH/LABELS_PATH at wherever you already put them. "
                f"See the README's \"Bring your own model\" note."
            )
    robot = Shepherd(sys.argv[1]) if len(sys.argv) > 1 else Shepherd()
    interpreter = _load_interpreter(MODEL_PATH)
    labels = _load_labels(LABELS_PATH)
    print(f"Looking for '{TARGET}'. Ctrl+C to stop.")

    try:
        while True:
            jpeg_bytes = robot.camera.snapshot("front")
            frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
            frame_height, frame_width = frame.shape[:2]

            matches = [det for det in detect(frame, interpreter, labels) if det.label == TARGET]

            if not matches:
                print("nothing found, standing by")
                robot.sport.stop()
                time.sleep(0.5)
                continue

            # No depth sensing here (plain monocular camera) — the
            # biggest box in frame is treated as the nearest match,
            # and that's the one to walk toward.
            target = max(matches, key=box_area)

            # -1 (target at the frame's left edge) .. 0 (centered) .. +1 (right edge)
            offset = ((target.x1 + target.x2) / 2 - frame_width / 2) / (frame_width / 2)
            vyaw = -offset * TURN_SPEED

            box_height_ratio = (target.y2 - target.y1) / frame_height  # 0 (small/far) .. 1 (fills the frame)
            if box_height_ratio >= CLOSE_ENOUGH:
                robot.sport.stop()
                print(f"Arrived at '{TARGET}' ({box_height_ratio:.0%} of frame height).")
                break

            print(f"target at {offset:+.2f}, {box_height_ratio:.0%} of frame height "
                  f"-> vx={FORWARD_SPEED:.2f} vyaw={vyaw:.2f}")
            robot.sport.move(FORWARD_SPEED, 0.0, vyaw)
            time.sleep(0.15)
    finally:
        robot.sport.stop()


if __name__ == "__main__":
    main()
