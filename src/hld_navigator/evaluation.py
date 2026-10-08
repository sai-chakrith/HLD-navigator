"""Evaluation accounting; annotation provenance must accompany every score."""


def warning_scores(actual, expected):
    """One-to-one match by allowed code and annotated location/text, never count info."""
    candidates = [w for w in actual if w.get("severity") == "blocking"]
    remaining = list(range(len(candidates)))
    matched, missed = [], []
    for annotation in expected:
        codes = annotation.get("codes", [annotation.get("code")])
        location = annotation.get("location", {})

        def matches(warning, codes=codes, location=location, annotation=annotation):
            actual_location = {**warning, **warning.get("location", {})}
            return (
                warning.get("code") in codes
                and all(actual_location.get(k) == v for k, v in location.items())
                and annotation.get("text_contains", "") in warning.get("text", "")
            )

        found = next((i for i in remaining if matches(candidates[i])), None)
        if found is None:
            missed.append(annotation)
        else:
            remaining.remove(found)
            matched.append({"expected": annotation, "actual": candidates[found]})
    tp, fp, fn = len(matched), len(remaining), len(missed)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "matched": matched,
        "missed": missed,
        "unexpected": [candidates[i] for i in remaining],
    }
