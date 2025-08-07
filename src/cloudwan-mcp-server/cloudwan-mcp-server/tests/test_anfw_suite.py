# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AWS Network Firewall (ANFW) test suite runner."""

import pytest
import sys
from pathlib import Path


def run_anfw_unit_tests():
    """Run ANFW unit tests."""
    unit_test_path = Path(__file__).parent / "unit" / "test_network_firewall_tools.py"
    return pytest.main([str(unit_test_path), "-v", "--tb=short"])


def run_anfw_integration_tests():
    """Run ANFW integration tests."""
    integration_test_path = Path(__file__).parent / "integration" / "test_network_firewall_integration.py"
    return pytest.main([str(integration_test_path), "-v", "--tb=short"])


def run_all_anfw_tests():
    """Run all ANFW tests."""
    test_paths = [
        Path(__file__).parent / "unit" / "test_network_firewall_tools.py",
        Path(__file__).parent / "integration" / "test_network_firewall_integration.py"
    ]
    return pytest.main([str(p) for p in test_paths] + ["-v", "--tb=short"])


if __name__ == "__main__":
    """Test runner for ANFW test suite."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "unit":
            exit_code = run_anfw_unit_tests()
        elif sys.argv[1] == "integration":
            exit_code = run_anfw_integration_tests()
        elif sys.argv[1] == "all":
            exit_code = run_all_anfw_tests()
        else:
            print("Usage: python test_anfw_suite.py [unit|integration|all]")
            sys.exit(1)
    else:
        exit_code = run_all_anfw_tests()
    
    sys.exit(exit_code)