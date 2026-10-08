from hld_navigator.evaluation import warning_scores


def test_warning_matching_is_one_to_one_and_location_specific():
    actual = [
        {"code": "unsupported_relationship", "severity": "blocking", "location": {"line": 3}},
        {"code": "unsupported_relationship", "severity": "blocking", "location": {"line": 3}},
        {"code": "blank_page", "severity": "info", "page": 2},
    ]
    expected = [
        {"codes": ["unsupported_relationship"], "location": {"line": 3}},
        {"codes": ["unsupported_relationship"], "location": {"line": 4}},
    ]
    score = warning_scores(actual, expected)
    assert (score["tp"], score["fp"], score["fn"]) == (1, 1, 1)
    assert score["precision"] == score["recall"] == 0.5


def test_zero_warning_denominators_are_unmeasured():
    score = warning_scores([], [])
    assert score["precision"] is score["recall"] is None


def test_table_location_and_text_must_match():
    actual = [{"code": "unsupported_table", "severity": "blocking", "table": 2}]
    expected = [{"code": "unsupported_table", "location": {"table": 1}}]
    assert warning_scores(actual, expected)["fn"] == 1


def test_missing_warning_annotations_are_not_silently_perfect():
    score = warning_scores([], [{"code": "unsupported_relationship", "location": {"line": 9}}])
    assert score["fn"] == 1
    assert score["recall"] == 0
