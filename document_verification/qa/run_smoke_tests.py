#!/usr/bin/env python3
"""
Esegue smoke test di verifica documenti caricando immagini (o image_id mock)
e confrontando i campi estratti con i ground truth attesi.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml


@dataclass
class SmokeTestResult:
    name: str
    success: bool
    http_status: int
    actual_status: Optional[str]
    field_accuracy: float
    details: List[str]


def load_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip().upper()


def compute_accuracy(expected_fields: Dict[str, Any], actual_payload: Dict[str, Any]) -> float:
    if not expected_fields:
        return 1.0

    matches = 0
    for field, expected_value in expected_fields.items():
        if normalize(actual_payload.get(field)) == normalize(expected_value):
            matches += 1
    return matches / len(expected_fields)


def run_case(case: Dict[str, Any], endpoint: str, defaults: Dict[str, Any]) -> SmokeTestResult:
    payload: Dict[str, Any] = {}
    files = None

    if case.get("issuer_country"):
        payload["issuer_country"] = case["issuer_country"]
    if case.get("document_type"):
        payload["document_type"] = case["document_type"]

    ocr_provider = case.get("ocr_provider") or defaults.get("default_ocr_provider")
    if ocr_provider:
        payload["ocr_provider"] = ocr_provider

    if case.get("image_path"):
        image_path = Path(case["image_path"])
        if not image_path.exists():
            return SmokeTestResult(
                name=case.get("name", image_path.name),
                success=False,
                http_status=0,
                actual_status=None,
                field_accuracy=0.0,
                details=[f"Immagine non trovata: {image_path}"],
            )
        files = {"image": image_path.open("rb")}
    elif case.get("image_id"):
        payload["image_id"] = case["image_id"]
    else:
        return SmokeTestResult(
            name=case.get("name", "unknown"),
            success=False,
            http_status=0,
            actual_status=None,
            field_accuracy=0.0,
            details=["image_id o image_path obbligatorio"],
        )

    request_kwargs: Dict[str, Any]
    if files:
        request_kwargs = {"data": payload, "files": files}
    else:
        request_kwargs = {"json": payload}

    response = requests.post(endpoint, **request_kwargs)
    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}

    allowed_statuses = case.get("allowed_statuses") or defaults.get("default_allowed_statuses") or []
    expected_status = case.get("expected_status")

    actual_status = data.get("status")
    expected_fields = case.get("expected_fields", {})
    field_accuracy = compute_accuracy(expected_fields, data)
    accuracy_threshold = case.get("min_field_accuracy") or defaults.get("default_min_field_accuracy", 1.0)

    details: List[str] = []
    success = True

    if response.status_code != 201:
        success = False
        details.append(f"HTTP atteso 201, ottenuto {response.status_code}")

    if expected_status:
        if actual_status != expected_status:
            success = False
            details.append(f"Status atteso {expected_status}, ottenuto {actual_status}")
    elif allowed_statuses and actual_status not in allowed_statuses:
        success = False
        details.append(f"Status {actual_status} non incluso in {allowed_statuses}")

    if field_accuracy < accuracy_threshold:
        success = False
        details.append(
            f"Accuratezza {field_accuracy:.2f} sotto soglia {accuracy_threshold:.2f}"
        )

    if files:
        files["image"].close()

    return SmokeTestResult(
        name=case.get("name", "unknown"),
        success=success,
        http_status=response.status_code,
        actual_status=actual_status,
        field_accuracy=field_accuracy,
        details=details,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Esegue i smoke test di verifica documenti")
    parser.add_argument("--config", required=True, type=Path, help="Percorso al file di configurazione YAML")
    parser.add_argument("--endpoint", required=False, help="Override dell'endpoint di verifica")
    args = parser.parse_args()

    config = load_config(args.config)
    endpoint = args.endpoint or config.get("endpoint")
    if not endpoint:
        raise SystemExit("Endpoint non specificato né in CLI né in config")

    tests = config.get("tests", [])
    if not tests:
        raise SystemExit("Nessun test definito nel file di configurazione")

    results: List[SmokeTestResult] = []
    for case in tests:
        result = run_case(case, endpoint, config)
        results.append(result)
        status_icon = "✅" if result.success else "❌"
        detail_text = f" | dettagli: {'; '.join(result.details)}" if result.details else ""
        print(
            f"{status_icon} {result.name}: HTTP {result.http_status}, stato={result.actual_status}, accuracy={result.field_accuracy:.2f}{detail_text}"
        )

    failures = [r for r in results if not r.success]
    print("\n---")
    print(f"Totale casi: {len(results)}, falliti: {len(failures)}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
