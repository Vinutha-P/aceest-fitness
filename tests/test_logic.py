"""Unit tests for the pure business logic in ``aceest.logic``."""
from datetime import date, timedelta

import pytest

from aceest.logic import (
    PROGRAMS,
    adherence_status,
    bmi_category,
    calculate_bmi,
    calculate_bmr,
    calculate_target_calories,
    get_program,
    list_programs,
    membership_status,
    total_workout_minutes,
    validate_client_payload,
    weekly_adherence_average,
)


class TestBMI:
    def test_calculate_bmi_known_value(self):
        # 70kg at 175cm -> 22.86
        assert calculate_bmi(70, 175) == 22.86

    def test_calculate_bmi_rounds_to_two_decimals(self):
        assert calculate_bmi(84.5, 178) == 26.67

    def test_calculate_bmi_zero_height_returns_none(self):
        assert calculate_bmi(70, 0) is None

    def test_calculate_bmi_none_height_returns_none(self):
        assert calculate_bmi(70, None) is None

    @pytest.mark.parametrize(
        "bmi,expected",
        [
            (17.0, "Underweight"),
            (22.5, "Normal"),
            (27.0, "Overweight"),
            (33.0, "Obese"),
            (None, "Unknown"),
        ],
    )
    def test_bmi_category(self, bmi, expected):
        assert bmi_category(bmi) == expected


class TestBMR:
    def test_calculate_bmr_male(self):
        # 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
        assert calculate_bmr(80, 180, 30, "male") == 1780

    def test_calculate_bmr_female(self):
        # 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25 -> 1345
        assert calculate_bmr(60, 165, 25, "female") == 1345

    def test_calculate_bmr_defaults_to_male(self):
        assert calculate_bmr(80, 180, 30) == calculate_bmr(80, 180, 30, "male")

    def test_calculate_bmr_negative_input_returns_zero(self):
        assert calculate_bmr(0, 180, 30) == 0

    @pytest.mark.parametrize(
        "goal,expected",
        [("cut", 1424), ("maintain", 1780), ("bulk", 2047)],
    )
    def test_calculate_target_calories(self, goal, expected):
        assert calculate_target_calories(1780, goal) == expected

    def test_calculate_target_calories_unknown_goal_defaults_to_maintain(self):
        assert calculate_target_calories(1780, "unknown") == 1780

    def test_calculate_target_calories_zero_bmr(self):
        assert calculate_target_calories(0, "cut") == 0


class TestAdherence:
    def test_average_of_records(self):
        assert weekly_adherence_average([("W1", 60), ("W2", 80)]) == 70.0

    def test_average_of_empty_is_zero(self):
        assert weekly_adherence_average([]) == 0.0

    @pytest.mark.parametrize(
        "average,expected",
        [
            (90, "On Track"),
            (85, "On Track"),
            (75, "Needs Improvement"),
            (70, "Needs Improvement"),
            (20, "At Risk"),
        ],
    )
    def test_adherence_status(self, average, expected):
        assert adherence_status(average) == expected


class TestWorkouts:
    def test_total_workout_minutes(self):
        workouts = [{"duration_min": 60}, {"duration_min": 45}, {"duration_min": 30}]
        assert total_workout_minutes(workouts) == 135

    def test_total_workout_minutes_empty(self):
        assert total_workout_minutes([]) == 0

    def test_total_workout_minutes_missing_key_defaults_to_zero(self):
        assert total_workout_minutes([{"notes": "no duration"}]) == 0


class TestMembership:
    def test_future_date_is_active(self):
        end = (date.today() + timedelta(days=90)).isoformat()
        assert membership_status(end) == "Active"

    def test_near_future_date_is_expiring_soon(self):
        end = (date.today() + timedelta(days=10)).isoformat()
        assert membership_status(end) == "Expiring Soon"

    def test_past_date_is_expired(self):
        end = (date.today() - timedelta(days=5)).isoformat()
        assert membership_status(end) == "Expired"

    def test_missing_date_is_inactive(self):
        assert membership_status(None) == "Inactive"

    def test_malformed_date_is_inactive(self):
        assert membership_status("not-a-date") == "Inactive"


class TestPrograms:
    def test_list_programs_returns_all_three(self):
        assert list_programs() == ["Beginner (BG)", "Fat Loss (FL)", "Muscle Gain (MG)"]

    def test_get_program_returns_definition(self):
        program = get_program("Fat Loss (FL)")
        assert program["calories"] == 2000
        assert "Back Squat" in program["workout"]

    def test_get_program_unknown_returns_none(self):
        assert get_program("Does Not Exist") is None

    def test_every_program_has_required_keys(self):
        for name in PROGRAMS:
            program = PROGRAMS[name]
            assert set(program) == {"workout", "diet", "calories", "colour"}


class TestValidation:
    def test_valid_payload(self):
        errors, cleaned = validate_client_payload(
            {"name": "Test User", "age": 30, "height": 180, "weight": 80}
        )
        assert errors == {}
        assert cleaned["name"] == "Test User"
        assert cleaned["age"] == 30
        assert cleaned["height"] == 180.0
        assert cleaned["weight"] == 80.0
        assert cleaned["program"] is None

    def test_missing_name_is_rejected(self):
        errors, _ = validate_client_payload(
            {"name": "  ", "age": 30, "height": 180, "weight": 80}
        )
        assert "name" in errors

    def test_missing_age_is_rejected(self):
        errors, _ = validate_client_payload(
            {"name": "Test", "age": "", "height": 180, "weight": 80}
        )
        assert "age" in errors

    def test_non_numeric_age_is_rejected(self):
        errors, _ = validate_client_payload(
            {"name": "Test", "age": "abc", "height": 180, "weight": 80}
        )
        assert "age" in errors

    def test_out_of_range_age_is_rejected(self):
        errors, _ = validate_client_payload(
            {"name": "Test", "age": 200, "height": 180, "weight": 80}
        )
        assert "age" in errors

    def test_non_numeric_height_is_rejected(self):
        errors, _ = validate_client_payload(
            {"name": "Test", "age": 30, "height": "tall", "weight": 80}
        )
        assert "height" in errors

    def test_negative_weight_is_rejected(self):
        errors, _ = validate_client_payload(
            {"name": "Test", "age": 30, "height": 180, "weight": -5}
        )
        assert "weight" in errors

    def test_unknown_program_is_rejected(self):
        errors, _ = validate_client_payload(
            {"name": "Test", "age": 30, "height": 180, "weight": 80, "program": "Yoga"}
        )
        assert "program" in errors

    def test_known_program_is_accepted(self):
        errors, cleaned = validate_client_payload(
            {
                "name": "Test",
                "age": 30,
                "height": 180,
                "weight": 80,
                "program": "Muscle Gain (MG)",
            }
        )
        assert errors == {}
        assert cleaned["program"] == "Muscle Gain (MG)"

    def test_all_errors_reported_at_once(self):
        errors, _ = validate_client_payload({})
        assert set(errors) == {"name", "age", "height", "weight"}
