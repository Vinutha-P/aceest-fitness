"""Pure business logic for ACEest Fitness & Gym.

These functions contain no Flask or database dependencies, which makes
them straightforward to unit test in isolation.
"""
from datetime import date, timedelta

PROGRAMS = {
    "Fat Loss (FL)": {
        "workout": (
            "Mon: 5x5 Back Squat + AMRAP\n"
            "Tue: EMOM 20min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: 10RFT Deadlifts/Box Jumps\n"
            "Fri: 30min Active Recovery"
        ),
        "diet": (
            "B: 3 Egg Whites + Oats Idli\n"
            "L: Grilled Chicken + Brown Rice\n"
            "D: Fish Curry + Millet Roti\n"
            "Target: 2,000 kcal"
        ),
        "calories": 2000,
        "colour": "#e74c3c",
    },
    "Muscle Gain (MG)": {
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
        ),
        "diet": (
            "B: 4 Eggs + PB Oats\n"
            "L: Chicken Biryani (250g Chicken)\n"
            "D: Mutton Curry + Jeera Rice\n"
            "Target: 3,200 kcal"
        ),
        "calories": 3200,
        "colour": "#2ecc71",
    },
    "Beginner (BG)": {
        "workout": (
            "Circuit Training: Air Squats, Ring Rows, Push-ups.\n"
            "Focus: Technique Mastery & Form (90% Threshold)"
        ),
        "diet": (
            "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.\n"
            "Protein: 120g/day"
        ),
        "calories": 2200,
        "colour": "#3498db",
    },
}

WORKOUT_TYPES = ("Strength", "Hypertrophy", "Cardio", "Mobility")

ADHERENCE_WARNING = 70
ADHERENCE_TARGET = 85


def list_programs():
    """Return the available program names."""
    return sorted(PROGRAMS)


def get_program(name):
    """Return the program definition for ``name`` or ``None`` if unknown."""
    return PROGRAMS.get(name)


def calculate_bmi(weight_kg, height_cm):
    """Calculate BMI, returning ``None`` when height is invalid."""
    if not height_cm or height_cm <= 0:
        return None
    return round(weight_kg / (height_cm / 100) ** 2, 2)


def bmi_category(bmi):
    """Map a BMI value onto a human readable category."""
    if bmi is None:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def calculate_bmr(weight_kg, height_cm, age, sex="male"):
    """Calculate BMR using the Mifflin-St Jeor equation."""
    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        return 0
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    return int(base + (5 if sex.lower() == "male" else -161))


def calculate_target_calories(bmr, goal):
    """Return the daily calorie target for a goal."""
    if bmr <= 0:
        return 0
    factor = {"cut": 0.8, "maintain": 1.0, "bulk": 1.15}.get(goal, 1.0)
    return round(bmr * factor)


def weekly_adherence_average(records):
    """Average the adherence values from ``[(week, adherence), ...]``."""
    values = [adherence for _, adherence in records]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def adherence_status(average):
    """Classify an adherence average into a status string."""
    if average >= ADHERENCE_TARGET:
        return "On Track"
    if average >= ADHERENCE_WARNING:
        return "Needs Improvement"
    return "At Risk"


def total_workout_minutes(workouts):
    """Sum the duration of every workout record."""
    return sum(workout.get("duration_min", 0) for workout in workouts)


def membership_status(membership_end):
    """Return the membership state given the renewal date string."""
    if not membership_end:
        return "Inactive"
    try:
        end = date.fromisoformat(membership_end)
    except ValueError:
        return "Inactive"
    today = date.today()
    if end < today:
        return "Expired"
    if end - today <= timedelta(days=30):
        return "Expiring Soon"
    return "Active"


def _validate_number(payload, field, label, errors, cleaned):
    """Validate an optional positive number field."""
    raw = payload.get(field)
    if raw in (None, ""):
        errors[field] = f"{label} is required."
        return
    try:
        value = float(raw)
    except (TypeError, ValueError):
        errors[field] = f"{label} must be a number."
        return
    if value <= 0:
        errors[field] = f"{label} must be greater than zero."
        return
    cleaned[field] = value


def _validate_age(payload, errors, cleaned):
    """Validate the required age field."""
    raw = payload.get("age")
    if raw in (None, ""):
        errors["age"] = "Age is required."
        return
    try:
        age = int(raw)
    except (TypeError, ValueError):
        errors["age"] = "Age must be a number."
        return
    if not 1 <= age <= 120:
        errors["age"] = "Age must be between 1 and 120."
        return
    cleaned["age"] = age


def validate_client_payload(payload):
    """Validate client input.

    Returns:
        A ``(errors, cleaned)`` tuple where ``errors`` is a dict of
        field -> message and ``cleaned`` is the normalised payload.
    """
    errors = {}
    cleaned = {}

    name = (payload.get("name") or "").strip()
    if not name:
        errors["name"] = "Name is required."
    cleaned["name"] = name

    _validate_age(payload, errors, cleaned)
    _validate_number(payload, "height", "Height", errors, cleaned)
    _validate_number(payload, "weight", "Weight", errors, cleaned)

    program = (payload.get("program") or "").strip()
    if program and program not in PROGRAMS:
        errors["program"] = f"Unknown program '{program}'."
    cleaned["program"] = program or None

    return errors, cleaned
