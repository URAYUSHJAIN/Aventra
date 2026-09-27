"""EXP-02 — FinBERT on Financial PhraseBank (Final Plan §25).

    py -3.12 -m ml.evaluation.finbert_phrasebank                 # Sentences_AllAgree
    py -3.12 -m ml.evaluation.finbert_phrasebank --subset 50Agree

IMPORTANT DISCLOSURE: ProsusAI/finBERT was fine-tuned on Financial PhraseBank. This
evaluation therefore overlaps with the model's training data and does NOT measure
generalisation; it verifies that the local model, tokenizer, label mapping and
aggregation used by Aventra reproduce the expected behaviour. Dataset licence:
CC BY-NC-SA 3.0 (Malo et al., 2014); the file is downloaded to data/external/ and not committed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import zipfile
from datetime import datetime, timezone

import requests
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from ml import config
from ml.news.finbert import get_news_analysis_service

URL = "https://huggingface.co/datasets/takala/financial_phrasebank/resolve/main/data/FinancialPhraseBank-v1.0.zip"
SHA256 = "0e1a06c4900fdae46091d031068601e3773ba067c7cecb5b0da1dcba5ce989a6"   # from the dataset repo's LFS metadata
LABELS = ["positive", "negative", "neutral"]
EXP_ID = "EXP-02_finbert_phrasebank"


def load_dataset(subset: str) -> list[tuple[str, str]]:
    path = config.DATA_DIR / "external" / "FinancialPhraseBank-v1.0.zip"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(requests.get(URL, timeout=60).content)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"Checksum mismatch for {path}: {digest}")
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.endswith(f"Sentences_{subset}.txt"))
        text = io.TextIOWrapper(archive.open(name), encoding="latin-1").read()
    rows = []
    for line in text.splitlines():
        sentence, _, label = line.rpartition("@")
        if sentence and label.strip() in LABELS:
            rows.append((sentence.strip(), label.strip()))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", default="AllAgree", choices=["AllAgree", "75Agree", "66Agree", "50Agree"])
    args = parser.parse_args(argv)
    rows = load_dataset(args.subset)
    service = get_news_analysis_service()
    started = time.perf_counter()
    predictions = [result["label"] for result in service.analyze_many([sentence for sentence, _ in rows])]
    seconds = time.perf_counter() - started
    truth = [label for _, label in rows]
    precision, recall, f1, support = precision_recall_fscore_support(truth, predictions, labels=LABELS, zero_division=0)
    macro = precision_recall_fscore_support(truth, predictions, labels=LABELS, average="macro", zero_division=0)
    result = {
        "experiment_id": EXP_ID, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": f"Financial PhraseBank v1.0, Sentences_{args.subset} (sha256 {SHA256[:16]}…)", "n_sentences": len(rows),
        "model": "ProsusAI/finBERT (local weights)", "model_version": service.model_version, "inference": "Aventra analyze_many (64-token sentence inputs)",
        "accuracy": accuracy_score(truth, predictions), "macro_precision": macro[0], "macro_recall": macro[1], "macro_f1": macro[2],
        "per_class": {label: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)} for label, p, r, f, s in zip(LABELS, precision, recall, f1, support)},
        "confusion_matrix": {"labels": LABELS, "rows_true_cols_pred": confusion_matrix(truth, predictions, labels=LABELS).tolist()},
        "inference_seconds_cpu": round(seconds, 1),
        "disclosure": "FinBERT was fine-tuned on Financial PhraseBank; these numbers overlap with its training data and are not a generalisation estimate.",
    }
    config.EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{EXP_ID}_{args.subset}"
    (config.EXPERIMENT_DIR / f"{stem}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    md = [f"# {EXP_ID} ({args.subset})", "", f"Generated {result['generated_at']} by `py -3.12 -m ml.evaluation.finbert_phrasebank --subset {args.subset}`.", "",
          f"> **Disclosure:** {result['disclosure']}", "", f"Dataset: {result['dataset']}, {len(rows)} sentences. Model: {result['model']} ({service.model_version}).", "",
          f"Accuracy **{result['accuracy']:.4f}**, macro-F1 **{result['macro_f1']:.4f}** (macro precision {result['macro_precision']:.4f}, macro recall {result['macro_recall']:.4f}).", "",
          "| Class | Precision | Recall | F1 | Support |", "|---|---|---|---|---|"]
    md += [f"| {label} | {v['precision']:.4f} | {v['recall']:.4f} | {v['f1']:.4f} | {v['support']} |" for label, v in result["per_class"].items()]
    md += ["", "Confusion matrix (rows = true, columns = predicted; order positive, negative, neutral):", "", "```"] + [str(row) for row in result["confusion_matrix"]["rows_true_cols_pred"]] + ["```", "", f"CPU inference time: {result['inference_seconds_cpu']} s."]
    (config.EXPERIMENT_DIR / f"{stem}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
