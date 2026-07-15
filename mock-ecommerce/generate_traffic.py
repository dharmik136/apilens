"""Drive realistic + error traffic across the mock store with combinatorial data shapes and async load control.

Usage:
    python generate_traffic.py --duration 30 --users 5 --rate 2
"""

from __future__ import annotations

import asyncio
import random
import sys
import time
import argparse
from typing import Callable, Any, Coroutine, Optional
from dataclasses import dataclass, field

import httpx

BASE = {
    "catalog": "http://localhost:9101",
    "users": "http://localhost:9102",
    "cart": "http://localhost:9103",
    "orders": "http://localhost:9104",
    "payments": "http://localhost:9105",
    "inventory": "http://localhost:9106",
}

SHOPPERS = [
    {"email": "neel.bhatt@example.com", "name": "Neel Bhatt", "tier": "premium", "password": "hunter2"},
    {"email": "aarav.patel@example.com", "name": "Aarav Patel", "tier": "standard", "password": "letmein"},
    {"email": "riya.shah@example.com", "name": "Riya Shah", "tier": "premium", "password": "s3cret"},
    {"email": "ananya.desai@example.com", "name": "Ananya Desai", "tier": "admin", "password": "admin!"},
    {"email": "kabir.pandya@example.com", "name": "Kabir Pandya", "tier": "standard", "password": "qwerty"},
]

GOOD_PRODUCTS = ["p1001", "p1002", "p1003", "p1006", "p1007", "p1009", "p1010", "p1011"]
OOS_PRODUCTS = ["p1005", "p1012"]
BAD_PRODUCTS = ["p9999", "nope", "p0000"]

# --- 3. Data-shape Generators ---
# A layer that mutates payloads along independent axes.

def gen_quantity_boundary() -> Any:
    return random.choice([0, 999999999, -1, 2147483647])

def gen_quantity_malformed() -> Any:
    return random.choice(["two", "", None, 3.14])

def gen_string_boundary() -> str:
    return random.choice(["", "A" * 5000, "drop table users;", "😂🔥💯", "\x00test"])

def gen_string_malformed() -> Any:
    return random.choice([123, None, ["list_instead_of_string"]])

def apply_data_shape(shape: str, base_payload: dict) -> dict:
    """Mutate base payload based on the shape requested."""
    if not base_payload or shape == "valid":
        return base_payload.copy()
        
    payload = base_payload.copy()
    keys = list(payload.keys())
    
    if shape == "boundary":
        for k, v in payload.items():
            if isinstance(v, int):
                payload[k] = gen_quantity_boundary()
            elif isinstance(v, str):
                payload[k] = gen_string_boundary()
                
    elif shape == "malformed":
        if keys:
            k = random.choice(keys)
            # Either drop a required field or change its type
            if random.random() < 0.3:
                del payload[k]
            else:
                if isinstance(payload[k], int):
                    payload[k] = gen_quantity_malformed()
                else:
                    payload[k] = gen_string_malformed()
                    
    elif shape == "adversarial":
        if keys:
            k = random.choice(keys)
            # Injection-looking strings or oversized payloads
            if isinstance(payload[k], str):
                payload[k] = "<script>alert(1)</script>" if random.random() > 0.5 else "A" * 100000
                
    return payload


# --- 2. Scenario Library ---

@dataclass
class Step:
    service: str
    method: str
    path: str
    label: str
    base_json: dict = field(default_factory=dict)
    base_params: dict = field(default_factory=dict)
    expected_status: int = 200

@dataclass
class Scenario:
    name: str
    steps: list[Step]

SCENARIOS = [
    Scenario(
        name="browse_and_cart",
        steps=[
            Step("catalog", "GET", "/products", "catalog /products", expected_status=200),
            Step("catalog", "GET", "/categories", "catalog /categories", expected_status=200),
            Step("catalog", "GET", "/products/{good_product}", "catalog /products/{id}", expected_status=200),
            Step("cart", "POST", "/cart/items", "cart add item", base_json={"product_id": "{good_product}", "quantity": 2}, expected_status=200),
            Step("cart", "GET", "/cart", "cart /cart", expected_status=200),
        ]
    ),
    Scenario(
        name="checkout_flow",
        steps=[
            Step("cart", "POST", "/cart/items", "cart add item", base_json={"product_id": "{good_product}", "quantity": 1}, expected_status=200),
            Step("cart", "POST", "/cart/checkout", "cart /checkout", expected_status=200),
        ]
    ),
    Scenario(
        name="bad_login",
        steps=[
            Step("users", "POST", "/login", "users /login (bad)", base_json={"email": "{email}", "password": "wrong"}, expected_status=401),
        ]
    ),
    Scenario(
        name="non_admin_users",
        steps=[
            Step("users", "POST", "/login", "users /login", base_json={"email": "{email}", "password": "{password}"}, expected_status=200),
            Step("users", "GET", "/users", "users /users (admin-only)", expected_status=403), # expected 403 if not admin
        ]
    ),
    Scenario(
        name="not_found_product",
        steps=[
            Step("catalog", "GET", "/products/{bad_product}", "catalog /products/{bad}", expected_status=404),
        ]
    ),
    Scenario(
        name="out_of_stock_checkout",
        steps=[
            Step("cart", "POST", "/cart/items", "cart add OOS item", base_json={"product_id": "{oos_product}", "quantity": 1}, expected_status=200),
            Step("cart", "POST", "/cart/checkout", "cart /checkout OOS", expected_status=409),
        ]
    )
]

def format_value(val: Any, ctx: dict) -> Any:
    if not isinstance(val, str):
        return val
    # Basic templating
    for k, v in ctx.items():
        val = val.replace(f"{{{k}}}", str(v))
    return val

def format_dict(d: dict, ctx: dict) -> dict:
    return {k: format_value(v, ctx) for k, v in d.items()}


# --- 5. Oracle / Verification Layer ---
class Oracle:
    def __init__(self):
        self.sent_requests = []
        self.lock = asyncio.Lock()
        
    async def record(self, scenario_name: str, step_label: str, shape: str, expected_status: int, actual_status: Optional[int], error: Optional[str] = None):
        async with self.lock:
            self.sent_requests.append({
                "scenario": scenario_name,
                "step": step_label,
                "shape": shape,
                "expected": expected_status,
                "actual": actual_status,
                "error": error,
                "timestamp": time.time()
            })
            
    def verify(self):
        print("\n" + "="*50)
        print("ORACLE VERIFICATION REPORT (STUB)")
        print("="*50)
        total = len(self.sent_requests)
        errors = [r for r in self.sent_requests if r["error"] is not None]
        print(f"Total Requests Dispatched: {total}")
        print(f"Connection/Timeout Errors: {len(errors)}")
        print("\n[!] Next Step for Oracle:")
        print("    Query APILens backend: GET /api/v1/projects/{id}/stats")
        print(f"    Assert that APILens ingested exactly {total} requests.")
        print("    Diff trace IDs to ensure no dropped spans across cart -> orders -> inventory.")
        print("="*50 + "\n")


# --- 4. Load Controller ---

async def execute_scenario(client: httpx.AsyncClient, scenario: Scenario, oracle: Oracle):
    shopper = random.choice(SHOPPERS)
    headers = {"X-User-Email": shopper["email"], "X-User-Name": shopper["name"], "X-User-Tier": shopper["tier"]}
    
    ctx = {
        "good_product": random.choice(GOOD_PRODUCTS),
        "bad_product": random.choice(BAD_PRODUCTS),
        "oos_product": random.choice(OOS_PRODUCTS),
        "email": shopper["email"],
        "password": shopper["password"]
    }
    
    for step in scenario.steps:
        # Combinatorial shape selection per step
        shape = random.choices(
            ["valid", "boundary", "malformed", "adversarial"], 
            weights=[0.70, 0.10, 0.10, 0.10],
            k=1
        )[0]
        
        url = BASE[step.service] + format_value(step.path, ctx)
        
        json_payload = apply_data_shape(shape, format_dict(step.base_json, ctx)) if step.base_json else None
        params_payload = apply_data_shape(shape, format_dict(step.base_params, ctx)) if step.base_params else None
        
        # If we mutated the payload to malformed/adversarial, the expected status might no longer hold.
        # But for a fuzzer, tracking 5xxs is the real goal.
        
        actual_status = None
        error_msg = None
        
        try:
            r = await client.request(step.method, url, headers=headers, json=json_payload, params=params_payload, timeout=10.0)
            actual_status = r.status_code
            status_str = f"{actual_status} (Expected {step.expected_status})" if shape == "valid" else f"{actual_status} (Fuzzed)"
            print(f"[{scenario.name:15} | {shape:9}] {step.method:6} {step.label:30} -> {status_str}")
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            print(f"[{scenario.name:15} | {shape:9}] {step.method:6} {step.label:30} -> ERR {error_msg}")
            
        await oracle.record(scenario.name, step.label, shape, step.expected_status, actual_status, error_msg)

async def load_worker(worker_id: int, client: httpx.AsyncClient, rate_limit: float, stop_event: asyncio.Event, oracle: Oracle):
    while not stop_event.is_set():
        scen = random.choice(SCENARIOS)
        await execute_scenario(client, scen, oracle)
        if rate_limit > 0:
            await asyncio.sleep(rate_limit * random.uniform(0.8, 1.2)) # Add slight jitter
        else:
            await asyncio.sleep(0.01)

async def run_load_test(duration: float, concurrent_users: int, requests_per_sec: float):
    print(f"Starting async load test: {concurrent_users} workers for {duration}s (~{requests_per_sec} scen/s total)...\n")
    
    # If 10 scen/s total and 5 workers, each worker needs to do 2 scen/s.
    rate_per_worker = requests_per_sec / concurrent_users if concurrent_users > 0 else 1
    rate_limit = 1.0 / rate_per_worker if rate_per_worker > 0 else 0
    
    stop_event = asyncio.Event()
    oracle = Oracle()
    
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=100)) as client:
        workers = [
            asyncio.create_task(load_worker(i, client, rate_limit, stop_event, oracle))
            for i in range(concurrent_users)
        ]
        
        await asyncio.sleep(duration)
        stop_event.set()
        
        # Wait for ongoing scenarios to finish gracefully
        await asyncio.gather(*workers)
        
    oracle.verify()

def main():
    parser = argparse.ArgumentParser(description="APILens Data Injector / Stress Tester")
    parser.add_argument("--duration", type=float, default=15.0, help="Test duration in seconds")
    parser.add_argument("--users", type=int, default=5, help="Number of concurrent shoppers (workers)")
    parser.add_argument("--rate", type=float, default=10.0, help="Target total scenarios per second")
    args = parser.parse_args()
    
    try:
        asyncio.run(run_load_test(args.duration, args.users, args.rate))
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")

if __name__ == "__main__":
    main()
