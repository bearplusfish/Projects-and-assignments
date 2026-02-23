import os
import re
import pickle

import numpy as np
import pandas as pd


def extract_chapter(code: str) -> str:
    code = (code or "").strip().upper().replace(" ", "")
    m = re.match(r"^([A-Z])", code)
    return m.group(1) if m else "X"


def extract_category3(code: str) -> str:
    code = (code or "").strip().upper().replace(" ", "")
    # Take letter + two digits before decimal, e.g., A09.1 -> A09
    m = re.match(r"^([A-Z][0-9]{2})", code)
    return m.group(1) if m else code.split(".")[0]


def main():
    # Resolve paths relative to this script file, independent of current working directory
    this_dir = os.path.dirname(os.path.abspath(__file__))
    labels_path = os.path.normpath(os.path.join(this_dir, '..', 'data', 'mimic3', 'full', 'labels_dictionary_full_raw.csv'))
    out_dir = os.path.normpath(os.path.join(this_dir, '..', 'data', 'mimic3'))
    os.makedirs(out_dir, exist_ok=True)

    df = pd.read_csv(labels_path)
    codes = df['icd9_code'].astype(str).str.strip().str.upper().tolist()

    chapters = sorted({extract_chapter(c) for c in codes})
    categories3 = sorted({extract_category3(c) for c in codes})
    codes_unique = sorted(set(codes))

    print(f"Chapters: {len(chapters)} | Categories(3-char): {len(categories3)} | Codes: {len(codes_unique)}")

    chap2idx = {c: i for i, c in enumerate(chapters)}
    cat2idx = {c: i for i, c in enumerate(categories3)}
    code2idx = {c: i for i, c in enumerate(codes_unique)}

    # Level matrices: Chapter (k1 x 1), Category (k2 x k1), Code (k3 x k2)
    C_chapters = np.ones((len(chapters), 1), dtype=np.float32)
    C_categories = np.zeros((len(categories3), len(chapters)), dtype=np.float32)
    C_codes = np.zeros((len(codes_unique), len(categories3)), dtype=np.float32)

    # Fill category -> chapter
    for cat in categories3:
        chap = extract_chapter(cat)
        C_categories[cat2idx[cat], chap2idx[chap]] = 1.0

    # Fill code -> category(3)
    for code in codes_unique:
        cat = extract_category3(code)
        if cat in cat2idx:
            C_codes[code2idx[code], cat2idx[cat]] = 1.0

    cluster_chain = [C_chapters, C_categories, C_codes]
    out_path = os.path.join(out_dir, 'hct.pkl')
    with open(out_path, 'wb') as f:
        pickle.dump(cluster_chain, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"HCT saved to {out_path}")


if __name__ == '__main__':
    main()
