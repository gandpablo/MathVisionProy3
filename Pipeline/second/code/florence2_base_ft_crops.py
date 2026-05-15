import argparse
import json
from io import BytesIO
from pathlib import Path

import requests
import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor


DEFAULT_MODEL = "microsoft/Florence-2-base-ft"


def load_image(path_or_url):
    if path_or_url.startswith(("http://", "https://")):
        response = requests.get(path_or_url, timeout=30)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    return Image.open(path_or_url).convert("RGB")


def load_model(model_id, device):
    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=dtype,
        trust_remote_code=True,
    ).to(device)
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    return model, processor


def run_florence_detection(image, model, processor, device, task_prompt):
    inputs = processor(text=task_prompt, images=image, return_tensors="pt").to(device)
    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024,
        num_beams=3,
        do_sample=False,
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(
        generated_text,
        task=task_prompt,
        image_size=(image.width, image.height),
    )
    return parsed.get(task_prompt, parsed)


def normalize_boxes(detection_result):
    boxes = detection_result.get("bboxes") or detection_result.get("boxes") or []
    labels = detection_result.get("labels") or ["region"] * len(boxes)
    normalized = []

    for index, box in enumerate(boxes):
        if len(box) != 4:
            continue
        x1, y1, x2, y2 = [int(round(float(value))) for value in box]
        if x2 <= x1 or y2 <= y1:
            continue
        normalized.append(
            {
                "index": index,
                "label": str(labels[index]) if index < len(labels) else "region",
                "bbox": [x1, y1, x2, y2],
            }
        )
    return normalized


def save_crops(image, boxes, output_dir, padding):
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    for item in boxes:
        x1, y1, x2, y2 = item["bbox"]
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(image.width, x2 + padding)
        y2 = min(image.height, y2 + padding)

        crop_path = output_dir / f"crop_{item['index']:03d}.png"
        image.crop((x1, y1, x2, y2)).save(crop_path)
        saved.append({**item, "bbox_padded": [x1, y1, x2, y2], "crop_path": str(crop_path)})

    (output_dir / "metadata.json").write_text(
        json.dumps(saved, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return saved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Local path or URL to the problem image.")
    parser.add_argument("--output-dir", default="florence2_crops")
    parser.add_argument("--model-id", default=DEFAULT_MODEL)
    parser.add_argument("--task", default="<OD>", help="Florence task prompt, e.g. <OD>.")
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    image = load_image(args.image)
    model, processor = load_model(args.model_id, args.device)
    detection = run_florence_detection(image, model, processor, args.device, args.task)
    boxes = normalize_boxes(detection)
    saved = save_crops(image, boxes, Path(args.output_dir), args.padding)
    print(json.dumps({"num_crops": len(saved), "crops": saved}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
