import os

import requests

API_BASE = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")


def _get(path, params=None):
    resp = requests.get(f"{API_BASE}{path}", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _post(path):
    resp = requests.post(f"{API_BASE}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_batch_summary():
    return _get("/api/batch/summary")


def get_drift():
    return _get("/api/batch/drift")


def get_records(bucket=None, action=None, status=None, limit=200):
    params = {"limit": limit}
    if bucket:
        params["bucket"] = bucket
    if action:
        params["action"] = action
    if status:
        params["status"] = status
    return _get("/api/records/", params)


def get_record(event_id):
    return _get(f"/api/records/{event_id}")


def get_exceptions():
    return _get("/api/records/exceptions/list")


def get_pending():
    return _get("/api/records/pending")


def approve_pending(decision_id):
    return _post(f"/api/records/pending/{decision_id}/execute")