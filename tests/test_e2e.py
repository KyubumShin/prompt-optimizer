"""End-to-end test for the Prompt Optimizer pipeline."""
from __future__ import annotations

import asyncio
import json
import time
import sys
import os
import subprocess
import signal
import requests

BASE_URL = "http://localhost:8000"
TEST_CSV = os.path.join(os.path.dirname(__file__), "test_data.csv")

def wait_for_server(timeout: int = 30) -> bool:
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if r.status_code == 200:
                print("Server is ready!")
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def test_create_run() -> int:
    """Create a run with the test CSV and return the run ID."""
    print("\n=== TEST 1: Create Run ===")

    with open(TEST_CSV, "rb") as f:
        files = {"file": ("test_data.csv", f, "text/csv")}
        data = {
            "name": "E2E Translation Test",
            "initial_prompt": "Translate the following English text to French:\n\n{text}",
            "expected_column": "expected_output",
            "config_json": json.dumps({
                "max_iterations": 2,
                "target_score": 0.95,
                "temperature": 0.3,
                "concurrency": 3,
            }),
        }
        r = requests.post(f"{BASE_URL}/api/runs", data=data, files=files)

    assert r.status_code == 200, f"Create run failed: {r.status_code} {r.text}"
    run = r.json()
    print(f"  Run created: id={run['id']}, name={run['name']}, status={run['status']}")
    assert run["name"] == "E2E Translation Test"
    assert run["status"] in ("pending", "running")
    return run["id"]


def test_list_runs(expected_count: int = 1):
    """Test listing runs."""
    print("\n=== TEST 2: List Runs ===")
    r = requests.get(f"{BASE_URL}/api/runs")
    assert r.status_code == 200
    runs = r.json()
    print(f"  Found {len(runs)} runs")
    assert len(runs) >= expected_count


def test_get_run(run_id: int) -> dict:
    """Test getting run detail."""
    print("\n=== TEST 3: Get Run Detail ===")
    r = requests.get(f"{BASE_URL}/api/runs/{run_id}")
    assert r.status_code == 200
    run = r.json()
    print(f"  Run: status={run['status']}, iterations={run['total_iterations_completed']}")
    return run


def test_wait_for_completion(run_id: int, timeout: int = 300) -> dict:
    """Wait for run to complete and return final state."""
    print("\n=== TEST 4: Wait for Pipeline Completion ===")
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{BASE_URL}/api/runs/{run_id}")
        run = r.json()
        status = run["status"]
        iters = run["total_iterations_completed"]
        print(f"  Status: {status}, Iterations: {iters}, Best score: {run.get('best_score')}", end="\r")

        if status in ("completed", "failed", "stopped"):
            print()
            print(f"  Final status: {status}")
            if run.get("best_score"):
                print(f"  Best score: {run['best_score']:.3f}")
            if run.get("error_message"):
                print(f"  Error: {run['error_message']}")
            return run

        time.sleep(3)

    print()
    raise TimeoutError(f"Run did not complete within {timeout}s")


def test_iterations(run_id: int):
    """Test iteration listing and detail."""
    print("\n=== TEST 5: Check Iterations ===")
    r = requests.get(f"{BASE_URL}/api/runs/{run_id}/iterations")
    assert r.status_code == 200
    iterations = r.json()
    print(f"  Found {len(iterations)} iterations")
    assert len(iterations) > 0

    for it in iterations:
        print(f"  Iteration {it['iteration_num']}: avg_score={it.get('avg_score')}")

    # Get first iteration detail
    first = iterations[0]
    r = requests.get(f"{BASE_URL}/api/runs/{run_id}/iterations/{first['iteration_num']}")
    assert r.status_code == 200
    detail = r.json()
    print(f"  Iteration {first['iteration_num']} detail: {len(detail.get('test_results', []))} test results")
    assert len(detail.get("test_results", [])) > 0

    # Check test results have scores and reasoning
    for tr in detail["test_results"][:3]:
        print(f"    Case {tr['test_case_index']}: score={tr.get('score')}, has_reasoning={bool(tr.get('judge_reasoning'))}")
        assert tr.get("score") is not None
        assert tr.get("judge_reasoning")


def test_logs(run_id: int):
    """Test log retrieval."""
    print("\n=== TEST 6: Check Logs ===")
    r = requests.get(f"{BASE_URL}/api/runs/{run_id}/logs")
    assert r.status_code == 200
    logs = r.json()
    print(f"  Found {len(logs)} log entries")
    assert len(logs) > 0

    stages = set(l["stage"] for l in logs)
    print(f"  Stages: {stages}")
    assert "system" in stages
    assert "test" in stages


def test_stop_nonrunning(run_id: int):
    """Test stopping a non-running run returns error."""
    print("\n=== TEST 7: Stop Non-Running (should fail) ===")
    r = requests.post(f"{BASE_URL}/api/runs/{run_id}/stop")
    print(f"  Status: {r.status_code} (expected 400)")
    assert r.status_code == 400


def test_not_found():
    """Test 404 for non-existent resources."""
    print("\n=== TEST 8: Not Found ===")
    r = requests.get(f"{BASE_URL}/api/runs/99999")
    print(f"  Get run 99999: {r.status_code} (expected 404)")
    assert r.status_code == 404

    r = requests.get(f"{BASE_URL}/api/runs/99999/iterations/1")
    print(f"  Get iteration: {r.status_code} (expected 404)")
    assert r.status_code == 404


def test_best_prompt(run: dict):
    """Verify best prompt was tracked."""
    print("\n=== TEST 9: Best Prompt ===")
    if run["status"] == "completed":
        assert run.get("best_prompt"), "Completed run should have best_prompt"
        assert run.get("best_score") is not None, "Completed run should have best_score"
        print(f"  Best prompt length: {len(run['best_prompt'])} chars")
        print(f"  Best score: {run['best_score']:.3f}")
    else:
        print(f"  Run status is {run['status']}, skipping best prompt check")


def test_human_feedback_empty():
    """Test human feedback with empty feedback (skip)."""
    print("\n=== TEST 10: Human Feedback Empty ===")

    # Create a run with human feedback enabled
    with open(TEST_CSV, "rb") as f:
        files = {"file": ("test_data.csv", f, "text/csv")}
        data = {
            "name": "Feedback Test",
            "initial_prompt": "Translate: {text}",
            "expected_column": "expected_output",
            "config_json": json.dumps({
                "max_iterations": 2,
                "target_score": 0.95,
                "temperature": 0.3,
                "concurrency": 3,
                "human_feedback_enabled": True,
            }),
        }
        r = requests.post(f"{BASE_URL}/api/runs", data=data, files=files)
    assert r.status_code == 200
    feedback_run_id = r.json()["id"]
    print(f"  Created run {feedback_run_id} with human feedback enabled")

    # Poll logs until we see "Waiting for human feedback"
    print("  Waiting for feedback checkpoint...")
    start = time.time()
    feedback_found = False
    while time.time() - start < 120:  # 2 minute timeout
        r = requests.get(f"{BASE_URL}/api/runs/{feedback_run_id}/logs")
        if r.status_code == 200:
            logs = r.json()
            for log in logs:
                if "Waiting for human feedback" in log.get("message", ""):
                    feedback_found = True
                    print(f"  Feedback checkpoint reached at iteration {log.get('iteration_id')}")
                    break
        if feedback_found:
            break
        time.sleep(2)

    assert feedback_found, "Pipeline did not reach feedback checkpoint"

    # Submit empty feedback
    print("  Submitting empty feedback...")
    r = requests.post(f"{BASE_URL}/api/runs/{feedback_run_id}/feedback", json={"feedback": ""})
    print(f"  Submit status: {r.status_code}")
    assert r.status_code == 200

    # Wait for run to complete (should not get stuck)
    print("  Waiting for pipeline to complete...")
    start = time.time()
    completed = False
    while time.time() - start < 180:  # 3 minute timeout
        r = requests.get(f"{BASE_URL}/api/runs/{feedback_run_id}")
        if r.status_code == 200:
            run = r.json()
            status = run["status"]
            iters = run["total_iterations_completed"]
            print(f"  Status: {status}, Iterations: {iters}", end="\r")
            if status in ("completed", "failed", "stopped"):
                completed = True
                print()
                print(f"  Final status: {status}, iterations: {iters}")
                break
        time.sleep(2)

    assert completed, "Pipeline did not complete after empty feedback"

    # Verify it completed at least 1 iteration
    r = requests.get(f"{BASE_URL}/api/runs/{feedback_run_id}")
    assert r.status_code == 200
    final_run = r.json()
    assert final_run["total_iterations_completed"] >= 1, "Should have completed at least 1 iteration"
    print(f"  Verified: Pipeline completed successfully after empty feedback")

    # Cleanup
    requests.delete(f"{BASE_URL}/api/runs/{feedback_run_id}")


def test_delete_run():
    """Test creating and deleting a run."""
    print("\n=== TEST 11: Delete Run ===")
    # Create a dummy run
    with open(TEST_CSV, "rb") as f:
        files = {"file": ("test_data.csv", f, "text/csv")}
        data = {
            "name": "Delete Test",
            "initial_prompt": "Translate: {text}",
            "expected_column": "expected_output",
            "config_json": json.dumps({"max_iterations": 1}),
        }
        r = requests.post(f"{BASE_URL}/api/runs", data=data, files=files)
    assert r.status_code == 200
    delete_id = r.json()["id"]

    # Wait a moment then delete
    time.sleep(2)
    r = requests.delete(f"{BASE_URL}/api/runs/{delete_id}")
    print(f"  Delete status: {r.status_code}")
    assert r.status_code == 200

    # Verify deleted
    r = requests.get(f"{BASE_URL}/api/runs/{delete_id}")
    assert r.status_code == 404
    print("  Verified: run deleted successfully")


def cleanup_runs():
    """Delete all existing runs for a clean test environment."""
    print("\nCleaning up existing runs...")
    r = requests.get(f"{BASE_URL}/api/runs")
    if r.status_code == 200:
        runs = r.json()
        for run in runs:
            requests.delete(f"{BASE_URL}/api/runs/{run['id']}")
        if runs:
            print(f"  Deleted {len(runs)} existing runs")
            time.sleep(2)
        else:
            print("  No existing runs to clean up")


def main():
    print("=" * 60)
    print("PROMPT OPTIMIZER - END TO END TEST")
    print("=" * 60)

    # Check server
    print("\nChecking server...")
    if not wait_for_server(timeout=10):
        print("ERROR: Server not running. Start with:")
        print("  cd /Users/kbshin/project/prompt-optimizer/backend && python3 -m uvicorn backend.main:app --reload")
        sys.exit(1)

    cleanup_runs()

    passed = 0
    failed = 0

    try:
        # Test 1: Create run
        run_id = test_create_run()
        passed += 1

        # Test 2: List runs
        test_list_runs()
        passed += 1

        # Test 3: Get run detail
        test_get_run(run_id)
        passed += 1

        # Test 4: Wait for completion
        final_run = test_wait_for_completion(run_id, timeout=300)
        passed += 1

        # Test 5: Check iterations
        test_iterations(run_id)
        passed += 1

        # Test 6: Check logs
        test_logs(run_id)
        passed += 1

        # Test 7: Stop non-running
        test_stop_nonrunning(run_id)
        passed += 1

        # Test 8: Not found
        test_not_found()
        passed += 1

        # Test 9: Best prompt
        test_best_prompt(final_run)
        passed += 1

        # Test 10: Human feedback empty
        test_human_feedback_empty()
        passed += 1

        # Test 11: Delete
        test_delete_run()
        passed += 1

    except AssertionError as e:
        print(f"\n  FAILED: {e}")
        failed += 1
    except Exception as e:
        print(f"\n  ERROR: {e}")
        failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of 11 tests")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
