"""Integration tests covering the Flask HTTP endpoints."""


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json()["status"] == "healthy"


class TestClientEndpoints:
    def test_list_clients_returns_seeded_data(self, client):
        response = client.get("/api/clients")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] >= 2
        assert any(c["name"] == "Arjun Mehta" for c in data["clients"])

    def test_client_payload_includes_derived_metrics(self, client):
        data = client.get("/api/clients").get_json()
        arjun = next(c for c in data["clients"] if c["name"] == "Arjun Mehta")
        assert arjun["bmi"] == 26.67
        assert arjun["bmi_category"] == "Overweight"
        assert arjun["bmr"] > 0
        assert arjun["adherence_status"] == "Needs Improvement"

    def test_get_single_client(self, client):
        response = client.get("/api/clients/Arjun Mehta")
        assert response.status_code == 200
        data = response.get_json()
        assert data["client"]["name"] == "Arjun Mehta"
        assert len(data["workouts"]) > 0
        assert len(data["progress"]) > 0

    def test_get_unknown_client_returns_404(self, client):
        response = client.get("/api/clients/Nobody")
        assert response.status_code == 404

    def test_create_client_success(self, client):
        payload = {"name": "Kiran Rao", "age": 31, "height": 175, "weight": 72}
        response = client.post("/api/clients", json=payload)
        assert response.status_code == 201
        assert client.get("/api/clients/Kiran Rao").status_code == 200

    def test_create_client_validation_errors(self, client):
        response = client.post("/api/clients", json={"name": ""})
        assert response.status_code == 400
        errors = response.get_json()["errors"]
        assert "name" in errors
        assert "age" in errors

    def test_create_duplicate_client_returns_409(self, client):
        payload = {"name": "Arjun Mehta", "age": 28, "height": 178, "weight": 84.5}
        response = client.post("/api/clients", json=payload)
        assert response.status_code == 409

    def test_create_client_with_unknown_program_returns_400(self, client):
        payload = {
            "name": "Bad Program",
            "age": 30,
            "height": 180,
            "weight": 80,
            "program": "Yoga",
        }
        assert client.post("/api/clients", json=payload).status_code == 400

    def test_delete_client_removes_dependents(self, client):
        assert client.delete("/api/clients/Priya Sharma").status_code == 200
        assert client.get("/api/clients/Priya Sharma").status_code == 404
        workouts = client.get("/api/workouts?client_name=Priya Sharma").get_json()
        assert workouts["count"] == 0

    def test_delete_unknown_client_returns_404(self, client):
        assert client.delete("/api/clients/Ghost").status_code == 404


class TestProgramEndpoints:
    def test_list_programs(self, client):
        data = client.get("/api/clients/programs/list").get_json()
        assert data["programs"] == ["Beginner (BG)", "Fat Loss (FL)", "Muscle Gain (MG)"]

    def test_get_program_detail(self, client):
        response = client.get("/api/clients/programs/Muscle Gain (MG)")
        assert response.status_code == 200
        assert response.get_json()["calories"] == 3200

    def test_get_unknown_program_returns_404(self, client):
        assert client.get("/api/clients/programs/Yoga").status_code == 404


class TestWorkoutEndpoints:
    def test_create_workout(self, client):
        payload = {
            "client_name": "Arjun Mehta",
            "date": "2026-10-01",
            "workout_type": "Strength",
            "duration_min": 50,
            "notes": "Deadlifts",
        }
        response = client.post("/api/workouts", json=payload)
        assert response.status_code == 201

    def test_create_workout_unknown_client_returns_404(self, client):
        payload = {
            "client_name": "Ghost",
            "workout_type": "Cardio",
            "duration_min": 30,
        }
        assert client.post("/api/workouts", json=payload).status_code == 404

    def test_create_workout_invalid_type_returns_400(self, client):
        payload = {
            "client_name": "Arjun Mehta",
            "workout_type": "Yoga",
            "duration_min": 30,
        }
        response = client.post("/api/workouts", json=payload)
        assert response.status_code == 400
        assert "workout_type" in response.get_json()["errors"]

    def test_create_workout_invalid_duration_returns_400(self, client):
        payload = {
            "client_name": "Arjun Mehta",
            "workout_type": "Cardio",
            "duration_min": -10,
        }
        assert client.post("/api/workouts", json=payload).status_code == 400

    def test_list_all_workouts_includes_total(self, client):
        data = client.get("/api/workouts").get_json()
        assert data["count"] >= 3
        assert data["total_minutes"] > 0

    def test_filter_workouts_by_client(self, client):
        data = client.get("/api/workouts?client_name=Arjun Mehta").get_json()
        assert data["count"] == 2


class TestProgressEndpoints:
    def test_create_progress(self, client):
        payload = {"client_name": "Arjun Mehta", "week": "W4", "adherence": 88}
        assert client.post("/api/progress", json=payload).status_code == 201

    def test_create_progress_out_of_range_returns_400(self, client):
        payload = {"client_name": "Arjun Mehta", "week": "W5", "adherence": 150}
        assert client.post("/api/progress", json=payload).status_code == 400

    def test_create_progress_missing_week_returns_400(self, client):
        payload = {"client_name": "Arjun Mehta", "adherence": 70}
        assert client.post("/api/progress", json=payload).status_code == 400

    def test_get_progress_average(self, client):
        data = client.get("/api/progress/Arjun Mehta").get_json()
        assert data["average"] == 71.0
        assert len(data["progress"]) == 3


class TestErrorHandling:
    def test_unknown_route_returns_json_404(self, client):
        response = client.get("/does-not-exist")
        assert response.status_code == 404
        assert response.get_json()["error"] == "Not found"

    def test_invalid_json_body_is_handled(self, client):
        response = client.post(
            "/api/clients", data="not json", content_type="application/json"
        )
        assert response.status_code == 400

    def test_method_not_allowed_returns_405(self, client):
        assert client.put("/health").status_code == 405
