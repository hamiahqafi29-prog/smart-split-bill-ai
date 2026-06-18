import argparse
import csv
import json
import mimetypes
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smart_split.ai import ExtractionError, extract_receipt
from smart_split.models import normalize_receipt


DEFAULT_MODELS = [
    "Qwen/Qwen3-VL-8B-Instruct:fastest",
    "CohereLabs/aya-vision-32b:fastest",
]


def run_benchmark(images: list[Path], models: list[str]) -> list[dict]:
    results = []
    for image in images:
        mime_type = mimetypes.guess_type(image.name)[0] or "image/jpeg"
        image_bytes = image.read_bytes()
        for model in models:
            started = time.perf_counter()
            try:
                receipt = normalize_receipt(
                    extract_receipt(
                        image_bytes,
                        mime_type,
                        provider="huggingface",
                        model=model,
                    )
                )
                status = "success"
                error = ""
            except ExtractionError as exc:
                receipt = None
                status = "error"
                error = str(exc)
            elapsed = round(time.perf_counter() - started, 3)
            result = {
                "image": str(image),
                "model": model,
                "status": status,
                "inference_seconds": elapsed,
                "error": error,
                "receipt": receipt,
            }
            results.append(result)
            print(
                f"[{status.upper()}] {image.name} | {model} | "
                f"{elapsed:.3f} seconds"
            )
    return results


def save_results(results: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark_results.json"
    csv_path = output_dir / "model_comparison.csv"

    json_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "image",
                "model",
                "status",
                "inference_seconds",
                "merchant",
                "item_count",
                "subtotal",
                "charge_count",
                "total",
                "error",
            ],
        )
        writer.writeheader()
        for result in results:
            receipt = result["receipt"] or {}
            writer.writerow(
                {
                    "image": result["image"],
                    "model": result["model"],
                    "status": result["status"],
                    "inference_seconds": result["inference_seconds"],
                    "merchant": receipt.get("merchant", ""),
                    "item_count": len(receipt.get("items", [])),
                    "subtotal": receipt.get("subtotal", ""),
                    "charge_count": len(receipt.get("charges", [])),
                    "total": receipt.get("total", ""),
                    "error": result["error"],
                }
            )

    print(f"\nJSON saved to: {json_path}")
    print(f"CSV saved to:  {csv_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark two OCR-free Hugging Face vision models."
    )
    parser.add_argument(
        "images",
        type=Path,
        nargs="+",
        help="Paths to two or more receipt images.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Hugging Face router model IDs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/results"),
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    missing = [str(image) for image in args.images if not image.is_file()]
    if missing:
        print("Missing image files: " + ", ".join(missing), file=sys.stderr)
        return 1
    if len(args.images) < 2:
        print("Provide at least two receipt images.", file=sys.stderr)
        return 1

    results = run_benchmark(args.images, args.models)
    save_results(results, args.output_dir)
    return 0 if all(result["status"] == "success" for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())

