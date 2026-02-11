"""End-to-end test for multi-column dataset support."""
from __future__ import annotations

import json
import time
import sys
import os
import requests

BASE_URL = "http://localhost:8000"
TEST_CSV = os.path.join(os.path.dirname(__file__), "test_data_multi_column.csv")

INITIAL_PROMPT = """You are a customer support agent. Respond to the customer based on the context below.

Product category: {product_category}
Customer tier: {customer_tier}
Customer sentiment: {sentiment}
Response language: {language}

Customer message: {customer_message}

Provide a helpful, empathetic response appropriate to the customer's tier and sentiment."""


def wait_for_server(timeout: int = 10) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def test_create_multi_column_run() -> int:
    """Create a run with the multi-column CSV."""
    print("\n=== TEST 1: Create Multi-Column Run ===")

    with open(TEST_CSV, "rb") as f:
        files = {"file": ("test_data_multi_column.csv", f, "text/csv")}
        data = {
            "name": "E2E Multi-Column Customer Support",
            "initial_prompt": INITIAL_PROMPT,
            "expected_column": "expected_output",
            "config_json": json.dumps({
                "max_iterations": 2,
                "target_score": 0.90,
                "temperature": 0.3,
                "concurrency": 3,
            }),
        }
        r = requests.post(f"{BASE_URL}/api/runs", data=data, files=files)

    assert r.status_code == 200, f"Create run failed: {r.status_code} {r.text}"
    run = r.json()
    print(f"  Run created: id={run['id']}, name={run['name']}")
    print(f"  Dataset columns: {run['dataset_columns']}")
    assert len(run["dataset_columns"]) == 6, f"Expected 6 columns, got {len(run['dataset_columns'])}"
    assert run["status"] in ("pending", "running")
    return run["id"]


def test_verify_columns(run_id: int):
    """Verify all 6 columns are stored correctly."""
    print("\n=== TEST 2: Verify Dataset Columns ===")
    r = requests.get(f"{BASE_URL}/api/runs/{run_id}")
    assert r.status_code == 200
    run = r.json()
    cols = run["dataset_columns"]
    expected_cols = ["customer_message", "product_category", "customer_tier", "sentiment", "language", "expected_output"]
    for c in expected_cols:
        assert c in cols, f"Missing column: {c}"
        print(f"  Column '{c}': OK")
    print(f"  All {len(cols)} columns verified")


def test_wait_for_completion(run_id: int, timeout: int = 300) -> dict:
    """Wait for pipeline to finish."""
    print("\n=== TEST 3: Wait for Pipeline Completion ===")
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{BASE_URL}/api/runs/{run_id}")
        run = r.json()
        status = run["status"]
        iters = run["total_iterations_completed"]
        score = run.get("best_score")
        print(f"  Status: {status}, Iterations: {iters}, Best score: {score}    ", end="\r")

        if status in ("completed", "failed", "stopped"):
            print()
            print(f"  Final status: {status}")
            if score:
                print(f"  Best score: {score:.3f}")
            if run.get("error_message"):
                print(f"  Error: {run['error_message']}")
            return run

        time.sleep(3)

    print()
    raise TimeoutError(f"Run did not complete within {timeout}s")


def test_multi_column_input_data(run_id: int):
    """Verify test results contain all input columns (not just 1)."""
    print("\n=== TEST 4: Verify Multi-Column Input Data ===")
    r = requests.get(f"{BASE_URL}/api/runs/{run_id}/iterations")
    assert r.status_code == 200
    iterations = r.json()
    assert len(iterations) > 0, "No iterations found"

    first = iterations[0]
    r = requests.get(f"{BASE_URL}/api/runs/{run_id}/iterations/{first['iteration_num']}")
    assert r.status_code == 200
    detail = r.json()
    results = detail.get("test_results", [])
    assert len(results) > 0, "No test results found"

    # Check that input_data has all 5 input columns
    input_cols = {"customer_message", "product_category", "customer_tier", "sentiment", "language"}
    for tr in results[:3]:
        data_keys = set(tr["input_data"].keys())
        missing = input_cols - data_keys
        assert not missing, f"Test case {tr['test_case_index']} missing input columns: {missing}"
        print(f"  Case {tr['test_case_index']}: {len(data_keys)} input cols, score={tr.get('score')}")
        print(f"    category={tr['input_data']['product_category']}, tier={tr['input_data']['customer_tier']}, sentiment={tr['input_data']['sentiment']}, lang={tr['input_data']['language']}")

    print(f"  All test results have {len(input_cols)} input columns")


def test_cleanup(run_id: int):
    """Delete the test run."""
    print("\n=== TEST 5: Cleanup ===")
    r = requests.delete(f"{BASE_URL}/api/runs/{run_id}")
    print(f"  Delete status: {r.status_code}")
    assert r.status_code == 200
    print("  Cleaned up successfully")


def main():
    print("=" * 60)
    print("PROMPT OPTIMIZER - MULTI-COLUMN DATASET E2E TEST")
    print("=" * 60)

    if not wait_for_server():
        print("ERROR: Server not running at", BASE_URL)
        sys.exit(1)
    print("Server is ready!")

    passed = 0
    failed = 0
    run_id = None

    try:
        run_id = test_create_multi_column_run()
        passed += 1

        test_verify_columns(run_id)
        passed += 1

        final_run = test_wait_for_completion(run_id, timeout=300)
        passed += 1

        test_multi_column_input_data(run_id)
        passed += 1

        test_cleanup(run_id)
        passed += 1

    except AssertionError as e:
        print(f"\n  FAILED: {e}")
        failed += 1
    except Exception as e:
        print(f"\n  ERROR: {type(e).__name__}: {e}")
        failed += 1
        if run_id:
            try:
                requests.delete(f"{BASE_URL}/api/runs/{run_id}")
            except Exception:
                pass

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of 5 tests")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
