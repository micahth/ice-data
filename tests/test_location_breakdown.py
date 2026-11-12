import pandas as pd

from arrest_common import clean_arrests, location_breakdown


def test_joint_locations_preserve_missing_values_and_state_fallback():
    data = pd.DataFrame({
        "apprehension_date": ["2025-01-01"] * 3,
        "duplicate_drop_row": [False, False, True],
        "apprehension_state_filled_in": [None, "TEXAS", "TEXAS"],
        "apprehension_state_original": ["TEXAS", None, None],
        "apprehension_aor": [None, "Dallas", "Dallas"],
        "apprehension_site_landmark": [" test ", None, "Excluded"],
    })
    result = location_breakdown(clean_arrests(data))
    assert set(result.state) == {"TEXAS"}
    assert result.groupby("dimension").arrests.sum().to_dict() == {"aor": 2, "landmark": 2}
    assert set(result[result.dimension == "landmark"].location) == {"TEST", "Unknown"}
