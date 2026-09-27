# EXP-02_finbert_phrasebank (AllAgree)

Generated 2026-09-27T15:06:03Z by `py -3.12 -m ml.evaluation.finbert_phrasebank --subset AllAgree`.

> **Disclosure:** FinBERT was fine-tuned on Financial PhraseBank; these numbers overlap with its training data and are not a generalisation estimate.

Dataset: Financial PhraseBank v1.0, Sentences_AllAgree (sha256 0e1a06c4900fdae4…), 2264 sentences. Model: ProsusAI/finBERT (local weights) (config-sha1:a182af27c725).

Accuracy **0.9717**, macro-F1 **0.9625** (macro precision 0.9505, macro recall 0.9759).

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| positive | 0.9473 | 0.9772 | 0.9620 | 570 |
| negative | 0.9058 | 0.9835 | 0.9430 | 303 |
| neutral | 0.9985 | 0.9669 | 0.9825 | 1391 |

Confusion matrix (rows = true, columns = predicted; order positive, negative, neutral):

```
[557, 12, 1]
[4, 298, 1]
[27, 19, 1345]
```

CPU inference time: 125.2 s.
