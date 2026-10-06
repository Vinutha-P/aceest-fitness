"""Blueprint exposing client management endpoints."""
from flask import Blueprint, jsonify, request

from .db import get_db
from .logic import (
    adherence_status,
    bmi_category,
    calculate_bmi,
    calculate_bmr,
    calculate_target_calories,
    get_program,
    list_programs,
    membership_status,
    validate_client_payload,
    weekly_adherence_average,
)

bp = Blueprint("clients", __name__, url_prefix="/api/clients")


@bp.get("")
def get_clients():
    """Return every client together with derived health metrics."""
    db = get_db()
    rows = db.execute(
        """
        SELECT name, age, height, weight, program, calories, target_weight,
               target_adherence, membership_status, membership_end
        FROM clients
        ORDER BY name
        """
    ).fetchall()

    clients = []
    for row in rows:
        bmi = calculate_bmi(row["weight"], row["height"])
        records = db.execute(
            "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id",
            (row["name"],),
        ).fetchall()
        average = weekly_adherence_average([(r["week"], r["adherence"]) for r in records])

        clients.append(
            {
                "name": row["name"],
                "age": row["age"],
                "height": row["height"],
                "weight": row["weight"],
                "program": row["program"],
                "calories": row["calories"],
                "target_weight": row["target_weight"],
                "target_adherence": row["target_adherence"],
                "membership_status": membership_status(row["membership_end"]),
                "membership_end": row["membership_end"],
                "bmi": bmi,
                "bmi_category": bmi_category(bmi),
                "bmr": calculate_bmr(row["weight"], row["height"], row["age"]),
                "average_adherence": average,
                "adherence_status": adherence_status(average),
            }
        )

    return jsonify({"clients": clients, "count": len(clients)})


@bp.post("")
def create_client():
    """Create a new client from the JSON request body."""
    payload = request.get_json(silent=True) or {}
    errors, cleaned = validate_client_payload(payload)
    if errors:
        return jsonify({"errors": errors}), 400

    program = cleaned.get("program")
    calories = get_program(program)["calories"] if program else None
    bmr = calculate_bmr(cleaned["weight"], cleaned["height"], cleaned["age"])
    target = calculate_target_calories(bmr, "cut") if bmr else None

    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO clients (name, age, height, weight, program, calories)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cleaned["name"],
                cleaned["age"],
                cleaned["height"],
                cleaned["weight"],
                cleaned["program"],
                calories or target,
            ),
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 - sqlite3.IntegrityError
        if "UNIQUE" in str(exc):
            return jsonify({"errors": {"name": "Client already exists."}}), 409
        raise

    return jsonify({"message": "Client created.", "name": cleaned["name"]}), 201


@bp.get("/<string:name>")
def get_client(name):
    """Return a single client with their workouts and progress."""
    db = get_db()
    client = db.execute(
        "SELECT * FROM clients WHERE name = ?", (name,)
    ).fetchone()
    if client is None:
        return jsonify({"error": f"No client named '{name}'."}), 404

    workouts = db.execute(
        """
        SELECT date, workout_type, duration_min, notes
        FROM workouts WHERE client_name = ? ORDER BY date DESC
        """,
        (name,),
    ).fetchall()
    progress = db.execute(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id",
        (name,),
    ).fetchall()

    bmi = calculate_bmi(client["weight"], client["height"])
    average = weekly_adherence_average(
        [(p["week"], p["adherence"]) for p in progress]
    )

    return jsonify(
        {
            "client": {
                "name": client["name"],
                "age": client["age"],
                "height": client["height"],
                "weight": client["weight"],
                "program": client["program"],
                "calories": client["calories"],
                "target_weight": client["target_weight"],
                "membership_status": membership_status(client["membership_end"]),
                "membership_end": client["membership_end"],
                "bmi": bmi,
                "bmi_category": bmi_category(bmi),
                "bmr": calculate_bmr(client["weight"], client["height"], client["age"]),
                "average_adherence": average,
                "adherence_status": adherence_status(average),
            },
            "workouts": [dict(w) for w in workouts],
            "progress": [dict(p) for p in progress],
        }
    )


@bp.delete("/<string:name>")
def delete_client(name):
    """Delete a client and all of their dependent records."""
    db = get_db()
    existing = db.execute("SELECT 1 FROM clients WHERE name = ?", (name,)).fetchone()
    if existing is None:
        return jsonify({"error": f"No client named '{name}'."}), 404

    for table in ("workouts", "progress", "clients"):
        if table != "clients":
            db.execute(f"DELETE FROM {table} WHERE client_name = ?", (name,))
    db.execute("DELETE FROM clients WHERE name = ?", (name,))
    db.commit()

    return jsonify({"message": f"Client '{name}' deleted."})


@bp.get("/programs/list")
def get_programs():
    """List all available training programs."""
    return jsonify({"programs": list_programs()})


@bp.get("/programs/<string:name>")
def get_program_detail(name):
    """Return the workout and diet plan for a single program."""
    program = get_program(name)
    if program is None:
        return jsonify({"error": f"No program named '{name}'."}), 404
    return jsonify({"name": name, **program})
