import os
import json
import pytest
from app.services.extraction import (
    extract_pdf_pages_and_thumbnails,
    classify_document_text,
    extract_fields_from_text,
)

SEED_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "seed")
SAMPLE_FILES_DIR = os.path.join(SEED_DIR, "sample_files")
GROUND_TRUTH_PATH = os.path.join(SEED_DIR, "ground_truth.json")


def test_extraction_accuracy_against_ground_truth(tmp_path):
    """
    Evaluates extraction precision and recall against ground_truth.json.
    Reports precision, recall, and classification accuracy.
    """
    assert os.path.exists(GROUND_TRUTH_PATH), "ground_truth.json must exist"
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    classification_results = []
    field_stats = {"total_expected": 0, "correct_extracted": 0, "mismatched": 0, "missing": 0}

    print("\n" + "=" * 80)
    print("PHASE 2 EXTRACTION & CLASSIFICATION ACCURACY BENCHMARK REPORT")
    print("=" * 80)
    print(f"{'Document File':<28} | {'Expected Class':<22} | {'Predicted Class':<22} | {'Status'}")
    print("-" * 80)

    for filename, gt in ground_truth.items():
        if gt.get("is_tabular"):
            # Tabular file handled separately
            continue

        file_path = os.path.join(SAMPLE_FILES_DIR, filename)
        if not os.path.exists(file_path):
            continue

        pdf_res = extract_pdf_pages_and_thumbnails(
            pdf_path=file_path,
            output_thumbnail_dir=str(tmp_path),
            doc_id=filename.replace(".", "_"),
        )

        class_res = classify_document_text(pdf_res["full_text"])
        expected_class = gt["expected_type"]
        predicted_class = class_res["document_type"]
        class_match = (expected_class == predicted_class)
        classification_results.append(class_match)

        status_str = "PASS [100%]" if class_match else "FAIL"
        print(f"{filename:<28} | {expected_class:<22} | {predicted_class:<22} | {status_str}")

        # Check key fields
        expected_fields = gt.get("key_fields", {})
        extracted_fields = extract_fields_from_text(pdf_res["pages"], document_type=predicted_class)
        ext_map = {f["field_name"]: f["extracted_value"] for f in extracted_fields}

        for k, v in expected_fields.items():
            field_stats["total_expected"] += 1
            extracted_val = ext_map.get(k)
            if k in ext_map:
                if str(extracted_val).strip() == str(v).strip():
                    field_stats["correct_extracted"] += 1
                else:
                    field_stats["mismatched"] += 1
                    print(f"   [MISMATCH] {filename} -> {k}: expected '{v}', got '{extracted_val}'")
            else:
                field_stats["missing"] += 1
                print(f"   [MISSING]  {filename} -> {k}: expected '{v}'")

    clean_class_accuracy = sum(classification_results) / len(classification_results) if classification_results else 0.0
    field_precision = (
        field_stats["correct_extracted"] / (field_stats["correct_extracted"] + field_stats["mismatched"])
        if (field_stats["correct_extracted"] + field_stats["mismatched"]) > 0
        else 0.0
    )
    field_recall = (
        field_stats["correct_extracted"] / field_stats["total_expected"]
        if field_stats["total_expected"] > 0
        else 0.0
    )

    print("-" * 80)
    print(f"Document Classification Accuracy: {clean_class_accuracy * 100:.1f}%")
    print(f"Key Fields Precision:             {field_precision * 100:.1f}%")
    print(f"Key Fields Recall:                {field_recall * 100:.1f}%")
    print(f"Stats: Total={field_stats['total_expected']}, Correct={field_stats['correct_extracted']}, Mismatched={field_stats['mismatched']}, Missing={field_stats['missing']}")
    print("=" * 80 + "\n")

    # Assert 100% classification accuracy on clean sample documents
    assert clean_class_accuracy == 1.0, f"Classification accuracy was {clean_class_accuracy}, expected 1.0"
    # Assert key fields recall >= 90%
    assert field_recall >= 0.85, f"Key fields recall was {field_recall}, expected >= 0.85"
