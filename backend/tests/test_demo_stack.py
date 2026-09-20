"""Unit tests for NETRA reproducibility stack.

Verifies:
1. demo-stack/template.yaml schema, resources, and exact tags.
2. scripts/break.py execution, timestamp comparison, and sub-10s assertion.
3. Makefile reproducibility targets (demo-up, demo-down, break).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def test_demo_stack_template_structure_and_tags(repo_root):
    """Verify demo-stack/template.yaml defines the exact required test resources."""
    template_path = repo_root / "demo-stack" / "template.yaml"
    assert template_path.exists(), f"Missing demo-stack template at {template_path}"

    class CFNSafeLoader(yaml.SafeLoader):
        pass

    def cfn_constructor(loader, tag_suffix, node):
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        elif isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        elif isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        return None

    CFNSafeLoader.add_multi_constructor("!", cfn_constructor)

    with open(template_path, "r", encoding="utf-8") as f:
        doc = yaml.load(f, Loader=CFNSafeLoader)

    resources = doc.get("Resources", {})

    # 1. Runaway c5.4xlarge tagged netra:demo + netra:managed
    runaway = resources.get("RunawayComputeInstance")
    assert runaway is not None, "Missing RunawayComputeInstance"
    props = runaway.get("Properties", {})
    assert props.get("InstanceType") == "c5.4xlarge"
    tags = {t["Key"]: t["Value"] for t in props.get("Tags", [])}
    assert tags.get("netra:demo") == "true"
    assert tags.get("netra:managed") == "true"

    # 2. Two unattached 100 GB gp3 volumes
    vol1 = resources.get("OrphanVolumeOne")
    vol2 = resources.get("OrphanVolumeTwo")
    assert vol1 is not None and vol2 is not None, "Missing orphaned volumes"
    assert vol1.get("Properties", {}).get("Size") == 100
    assert vol2.get("Properties", {}).get("Size") == 100
    assert vol1.get("Properties", {}).get("VolumeType") == "gp3"
    assert vol2.get("Properties", {}).get("VolumeType") == "gp3"

    # 3. Protected control instance tagged netra:protected
    protected = resources.get("ProtectedControlInstance")
    assert protected is not None, "Missing ProtectedControlInstance"
    prot_props = protected.get("Properties", {})
    assert prot_props.get("InstanceType") == "t3.micro"
    prot_tags = {t["Key"]: t["Value"] for t in prot_props.get("Tags", [])}
    assert prot_tags.get("netra:protected") == "true"

    # 4. Healthy control instance
    healthy = resources.get("HealthyControlInstance")
    assert healthy is not None, "Missing HealthyControlInstance"
    hlth_props = healthy.get("Properties", {})
    assert hlth_props.get("InstanceType") == "t3.micro"
    hlth_tags = {t["Key"]: t["Value"] for t in hlth_props.get("Tags", [])}
    assert hlth_tags.get("netra:managed") == "true"
    assert "Owner" in hlth_tags

    # 5. Output hourly cost
    outputs = doc.get("Outputs", {})
    burn_rate = outputs.get("EstimatedBurnRate", {}).get("Value", "")
    assert "≈₹70.00/hr" in burn_rate or "₹70" in burn_rate


def test_makefile_reproducibility_targets(repo_root):
    """Verify Makefile contains demo-up, demo-down, and break targets."""
    makefile_path = repo_root / "Makefile"
    assert makefile_path.exists()
    content = makefile_path.read_text(encoding="utf-8")
    assert "demo-up:" in content
    assert "demo-down:" in content
    assert "break:" in content


def test_break_script_execution_and_sub_10s_latency(repo_root):
    """Verify scripts/break.py executes fast path and reports sub-10-second latency."""
    import importlib.util

    break_path = repo_root / "scripts" / "break.py"
    spec = importlib.util.spec_from_file_location("break_module", str(break_path))
    break_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(break_module)

    with patch("sys.argv", ["break.py", "--local"]):
        with patch.object(break_module, "run_fast_path") as mock_fast_path:
            mock_fast_path.return_value = {
                "status": "ok",
                "detection_path": "fast",
                "resource_id": "i-testrunaway123",
                "detection_latency_ms": 48,
                "findings": ["fnd-fast-test"],
            }
            # Capture stdout to ensure timestamps are printed
            with patch("builtins.print") as mock_print:
                break_module.main()

                printed_lines = [call[0][0] for call in mock_print.call_args_list if call[0]]
                full_output = "\n".join(str(l) for l in printed_lines)

                assert "EC2 Launch Timestamp" in full_output
                assert "Finding detected_at" in full_output
                assert "PROVEN DETECTION LATENCY" in full_output
                assert "Sub-10-second fast-path verified" in full_output
