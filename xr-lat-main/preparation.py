import argparse
import os
from typing import List, Dict
import pandas as pd


def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def _extract_text_and_labels(ex):
    if "text" not in ex:
        raise KeyError("Sample missing 'text' field. Please use a *bigbio_text configuration or check dataset version.")
    text = ex["text"] or ""

    labels = ex.get("labels")
    if labels is None:
        # Some datasets may use 'label' instead of 'labels'
        labels = ex.get("label")
    if labels is None:
        raise KeyError("Sample missing 'labels' field. Please select a *bigbio_text configuration (e.g. codiesp_D_bigbio_text).")

    # Normalize to a list of strings
    if isinstance(labels, str):
        labels = [labels]
    elif isinstance(labels, (list, tuple)):
        labels = [str(x) for x in labels if str(x).strip()]
    else:
        raise ValueError(f"Unsupported type for labels field: {type(labels)}")

    return text, labels


def _build_label_vocab(train_ds) -> List[str]:
    vocab = set()
    for ex in train_ds:
        _, labels = _extract_text_and_labels(ex)
        vocab.update(labels)
    return sorted(vocab)


def _to_multihot(labels: List[str], code2idx: Dict[str, int], n_labels: int) -> List[int]:
    vec = [0] * n_labels
    for c in labels:
        idx = code2idx.get(c)
        if idx is not None:
            vec[idx] = 1
    return vec


def _convert_split(split_ds, code2idx: Dict[str, int], out_csv: str):
    n = len(code2idx)
    rows = []
    for ex in split_ds:
        text, labels = _extract_text_and_labels(ex)
        rows.append({
            "text": text,
            # The repo reads this field using ast.literal_eval, so we store a Python list string
            "labels": str(_to_multihot(labels, code2idx, n))
        })
    pd.DataFrame(rows).to_csv(out_csv, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        default="codiesp_D_bigbio_text",
        help="datasets configuration name: codiesp_D_bigbio_text / codiesp_P_bigbio_text"
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default=os.path.join("data", "mimic3", "full"),
        help="output directory (compatible with repository training scripts)"
    )
    args = parser.parse_args()

    # Delayed import to allow static checking without network access
    from datasets import load_dataset

    print(f"Loading dataset bigbio/codiesp configuration: {args.config}")
    ds_dict = load_dataset("bigbio/codiesp", args.config)

    # Split name compatibility
    train_ds = ds_dict.get("train")
    dev_ds = ds_dict.get("validation") or ds_dict.get("dev")
    test_ds = ds_dict.get("test")
    if train_ds is None or dev_ds is None or test_ds is None:
        raise ValueError("Missing train/dev/test splits. Please verify dataset configuration and version.")

    print("Building label vocabulary (based on training set)...")
    vocab = _build_label_vocab(train_ds)
    code2idx = {c: i for i, c in enumerate(vocab)}
    print(f"Number of labels: {len(vocab)}")

    _ensure_dir(args.out_dir)

    # Label dictionary: keep column name 'icd9_code' for compatibility (even if using ICD-10-ES codes)
    dict_csv = os.path.join(args.out_dir, "labels_dictionary_full_raw.csv")
    pd.DataFrame({"icd9_code": vocab}).to_csv(dict_csv, index=False)

    # Convert splits
    train_csv = os.path.join(args.out_dir, "train_data_full_raw.csv")
    dev_csv = os.path.join(args.out_dir, "dev_data_full_raw.csv")
    test_csv = os.path.join(args.out_dir, "test_data_full_raw.csv")

    _convert_split(train_ds, code2idx, train_csv)
    _convert_split(dev_ds, code2idx, dev_csv)
    _convert_split(test_ds, code2idx, test_csv)


if __name__ == "__main__":
    main()
