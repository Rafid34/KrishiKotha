"""Verification of static JSON data against PROJECT_SPEC.md lines 601-629."""
import json
from pathlib import Path

DATA_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "static"

EXPECTED_DISTRICTS = [
    {
        "id": "sylhet",
        "name_en": "Sylhet",
        "name_bn": "সিলেট",
        "division": "Sylhet",
        "lat": 24.8949,
        "lon": 91.8687,
        "coastal_distance_km": 250,
    },
    {
        "id": "sunamganj",
        "name_en": "Sunamganj",
        "name_bn": "সুনামগঞ্জ",
        "division": "Sylhet",
        "lat": 25.0658,
        "lon": 91.4073,
        "coastal_distance_km": 280,
    },
    {
        "id": "khulna",
        "name_en": "Khulna",
        "name_bn": "খুলনা",
        "division": "Khulna",
        "lat": 22.8456,
        "lon": 89.5403,
        "coastal_distance_km": 60,
    },
    {
        "id": "satkhira",
        "name_en": "Satkhira",
        "name_bn": "সাতক্ষীরা",
        "division": "Khulna",
        "lat": 22.7185,
        "lon": 89.0705,
        "coastal_distance_km": 30,
    },
    {
        "id": "barishal",
        "name_en": "Barishal",
        "name_bn": "বরিশাল",
        "division": "Barishal",
        "lat": 22.7010,
        "lon": 90.3535,
        "coastal_distance_km": 70,
    },
    {
        "id": "rajshahi",
        "name_en": "Rajshahi",
        "name_bn": "রাজশাহী",
        "division": "Rajshahi",
        "lat": 24.3745,
        "lon": 88.6042,
        "coastal_distance_km": 350,
    },
    {
        "id": "rangpur",
        "name_en": "Rangpur",
        "name_bn": "রংপুর",
        "division": "Rangpur",
        "lat": 25.7439,
        "lon": 89.2752,
        "coastal_distance_km": 330,
    },
    {
        "id": "chattogram",
        "name_en": "Chattogram",
        "name_bn": "চট্টগ্রাম",
        "division": "Chattogram",
        "lat": 22.3569,
        "lon": 91.7832,
        "coastal_distance_km": 10,
    },
]

# Typed from PROJECT_SPEC.md lines 614 to 629:
# Month names to numbers: Mar=3, Apr=4, May=5, Jun=6, Jul=7, Aug=8, Sep=9, Oct=10, Nov=11, Dec=12, Jan=1, Feb=2
EXPECTED_CROP_STAGES = {
    "aman": [
        {"key": "nursery", "start_month": 6, "end_month": 7, "flood": 1.0, "drought": 1.2, "salt": 0.8},
        {"key": "transplanting", "start_month": 7, "end_month": 8, "flood": 1.1, "drought": 1.2, "salt": 0.9},
        {"key": "vegetative", "start_month": 8, "end_month": 9, "flood": 1.0, "drought": 1.0, "salt": 1.0},
        {"key": "flowering", "start_month": 9, "end_month": 10, "flood": 1.1, "drought": 1.2, "salt": 1.0},
        {"key": "grain_filling_harvest", "start_month": 11, "end_month": 12, "flood": 1.3, "drought": 0.5, "salt": 0.6},
    ],
    "boro": [
        {"key": "seedbed", "start_month": 11, "end_month": 12, "flood": 0.8, "drought": 0.8, "salt": 0.9},
        {"key": "transplanting", "start_month": 12, "end_month": 1, "flood": 0.6, "drought": 1.0, "salt": 1.2},
        {"key": "vegetative", "start_month": 1, "end_month": 2, "flood": 0.6, "drought": 1.1, "salt": 1.2},
        {"key": "flowering", "start_month": 3, "end_month": 3, "flood": 0.8, "drought": 1.2, "salt": 1.3},
        {"key": "grain_filling_harvest", "start_month": 4, "end_month": 5, "flood": 1.3, "drought": 0.6, "salt": 1.0},
    ],
    "aus": [
        {"key": "sowing", "start_month": 3, "end_month": 4, "flood": 1.0, "drought": 1.1, "salt": 0.9},
        {"key": "vegetative", "start_month": 5, "end_month": 6, "flood": 1.1, "drought": 1.0, "salt": 0.8},
        {"key": "flowering", "start_month": 6, "end_month": 7, "flood": 1.1, "drought": 1.1, "salt": 0.7},
        {"key": "grain_filling_harvest", "start_month": 7, "end_month": 8, "flood": 1.3, "drought": 0.5, "salt": 0.5},
    ],
}


def test_districts_json_matches_spec():
    path = DATA_STATIC_DIR / "districts.json"
    districts = json.loads(path.read_text(encoding="utf-8"))

    assert len(districts) == len(EXPECTED_DISTRICTS)

    for actual, expected in zip(districts, EXPECTED_DISTRICTS):
        assert actual["id"] == expected["id"]
        assert actual["name_en"] == expected["name_en"]
        assert actual["name_bn"] == expected["name_bn"]
        assert actual["division"] == expected["division"]
        assert actual["lat"] == expected["lat"]
        assert actual["lon"] == expected["lon"]
        assert actual["coastal_distance_km"] == expected["coastal_distance_km"]


def test_crops_json_matches_spec():
    path = DATA_STATIC_DIR / "crops.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    crops = data["crops"]

    actual_by_id = {c["id"]: c["stages"] for c in crops}
    assert set(actual_by_id.keys()) == set(EXPECTED_CROP_STAGES.keys())

    for crop_id, expected_stages in EXPECTED_CROP_STAGES.items():
        actual_stages = actual_by_id[crop_id]
        assert len(actual_stages) == len(expected_stages)
        for act, exp in zip(actual_stages, expected_stages):
            assert act["key"] == exp["key"]
            assert act["start_month"] == exp["start_month"]
            assert act["end_month"] == exp["end_month"]
            assert act["flood"] == exp["flood"]
            assert act["drought"] == exp["drought"]
            assert act["salt"] == exp["salt"]
