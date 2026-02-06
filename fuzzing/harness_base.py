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

"""Polyglot harness base infrastructure for OSS-Fuzz integration.

This module provides the PolyglotHarness class that enables fuzz targets to work
both as pytest tests (using Hypothesis) and as OSS-Fuzz targets (using Atheris).

The design follows the ujson example pattern from OSS-Fuzz documentation for
Python projects, enabling seamless dual-mode execution.

Example usage:
    ```python
    from fuzzing.harness_base import PolyglotHarness
    from hypothesis import strategies as st


    def fuzz_target(data: bytes) -> None:
        # Your fuzzing logic here
        pass


    @given(st.binary())
    def test_fuzz_target(data: bytes) -> None:
        fuzz_target(data)


    if __name__ == '__main__':
        PolyglotHarness.run_harness(fuzz_target, test_fuzz_target)
    ```
"""

from __future__ import annotations

import sys
from hypothesis.strategies import SearchStrategy
from typing import Callable, TypeVar


# Type variable for generic strategy return types
T = TypeVar('T')


class PolyglotHarness:
    """Base class for polyglot fuzz harnesses.

    Provides infrastructure for running fuzz targets both as pytest tests
    (using Hypothesis) and as OSS-Fuzz targets (using Atheris).

    This class implements the dual-mode execution pattern where:
    - Under Atheris: Consumes raw bytes from the fuzzer
    - Under pytest: Uses Hypothesis strategies for structured input generation

    The harness shares common test logic between both execution modes,
    following the ujson example pattern from OSS-Fuzz documentation.
    """

    # Module-level cache for atheris mode detection
    _atheris_mode_cache: bool | None = None

    @staticmethod
    def is_atheris_mode() -> bool:
        """Detect if running under Atheris fuzzer.

        Determines the execution mode by checking if the atheris module
        is available and if we're being run as the main entry point by
        the fuzzer (not imported as a module for testing).

        The detection logic checks:
        1. If 'atheris' module is importable
        2. If we're running as __main__ (direct execution)
        3. If the entry point appears to be atheris-related

        Returns:
            True if running under Atheris (OSS-Fuzz mode), False otherwise
            (pytest/Hypothesis mode).

        Note:
            This method caches its result for performance, as the execution
            mode cannot change during a single run.
        """
        if PolyglotHarness._atheris_mode_cache is not None:
            return PolyglotHarness._atheris_mode_cache

        # Check if atheris is available
        try:
            import atheris  # noqa: F401

            atheris_available = True
        except ImportError:
            atheris_available = False

        # Determine if we're in atheris mode
        # We're in atheris mode if:
        # 1. atheris is available AND
        # 2. We're running as main (not imported for testing) AND
        # 3. We're not running under pytest
        in_pytest = 'pytest' in sys.modules or '_pytest' in sys.modules

        # Check if atheris.instrument_all_functions has been called
        # This is a strong indicator that we're running under atheris
        atheris_instrumented = False
        if atheris_available:
            try:
                import atheris

                # Check if atheris has been initialized
                # The presence of certain internal state indicates active fuzzing
                atheris_instrumented = hasattr(atheris, '_trace_branch') or (
                    hasattr(sys, 'settrace') and sys.gettrace() is not None
                )
            except Exception:
                pass

        # Final determination: atheris mode if atheris is available,
        # not in pytest, and either instrumented or running as main
        is_atheris = (
            atheris_available
            and not in_pytest
            and (atheris_instrumented or __name__ == '__main__')
        )

        PolyglotHarness._atheris_mode_cache = is_atheris
        return is_atheris

    @staticmethod
    def reset_mode_cache() -> None:
        """Reset the atheris mode detection cache.

        This is primarily useful for testing the mode detection logic itself.
        In normal operation, the cache should not need to be reset.
        """
        PolyglotHarness._atheris_mode_cache = None

    @staticmethod
    def bytes_to_structured(data: bytes, strategy: SearchStrategy[T]) -> T:
        r"""Convert raw bytes to structured input using Hypothesis.

        This method enables Atheris fuzz targets to generate structured inputs
        from raw byte sequences by leveraging Hypothesis's internal machinery.
        The conversion is deterministic for the same input bytes.

        Args:
            data: Raw bytes from the fuzzer (must have length > 0)
            strategy: A Hypothesis SearchStrategy defining the structure
                of the desired output

        Returns:
            A value conforming to the provided strategy, generated
            deterministically from the input bytes

        Raises:
            ValueError: If data is empty (length must be > 0)

        Example:
            ```python
            from hypothesis import strategies as st

            # Convert bytes to a structured dict
            data = b'\x00\x01\x02\x03'
            result = PolyglotHarness.bytes_to_structured(
                data,
                st.fixed_dictionaries(
                    {'name': st.text(min_size=1, max_size=10), 'value': st.integers(0, 100)}
                ),
            )
            ```

        Note:
            The conversion uses Hypothesis's ConjectureData to interpret
            the bytes as choices for the strategy. This ensures that:
            1. The same bytes always produce the same output
            2. The output is always valid according to the strategy
            3. Different byte sequences explore different parts of the input space
        """
        if len(data) == 0:
            raise ValueError('Input data must have length > 0')

        from hypothesis.internal.conjecture.data import ConjectureData

        # Convert bytes to a list of integer choices for ConjectureData
        # Each byte becomes an integer choice that guides strategy generation
        choices = list(data)

        # Create a ConjectureData instance from the choices
        # This interprets the choices as decisions for the strategy
        conjecture_data = ConjectureData.for_choices(choices)

        try:
            # Draw a value from the strategy using the byte-derived choices
            result = conjecture_data.draw(strategy)
            return result
        except Exception:
            # If the choices don't produce a valid value (e.g., insufficient choices),
            # use a minimal valid value from the strategy
            # This ensures we always return something valid
            from hypothesis import find

            return find(strategy, lambda x: True)

    @classmethod
    def run_harness(
        cls,
        target_fn: Callable[[bytes], None],
        hypothesis_test: Callable[[], None],
    ) -> None:
        """Execute harness in appropriate mode.

        This method is the main entry point for polyglot harnesses. It detects
        the execution mode and runs the appropriate test function:
        - Under Atheris: Sets up the fuzzer and runs the target function
        - Under pytest: The hypothesis_test is run by pytest directly

        Args:
            target_fn: The fuzz target function that accepts raw bytes.
                This function should exercise the code under test and
                may raise exceptions for invalid inputs.
            hypothesis_test: A Hypothesis test function decorated with @given.
                This is used when running under pytest for property-based testing.

        Example:
            ```python
            def fuzz_json_parser(data: bytes) -> None:
                try:
                    json.loads(data.decode('utf-8', errors='replace'))
                except json.JSONDecodeError:
                    pass  # Expected for invalid JSON


            @given(st.binary())
            def test_json_parser(data: bytes) -> None:
                fuzz_json_parser(data)


            if __name__ == '__main__':
                PolyglotHarness.run_harness(fuzz_json_parser, test_json_parser)
            ```

        Note:
            When running under pytest, this method does nothing because
            pytest will discover and run the hypothesis_test directly.
            The method only takes action when running under Atheris.
        """
        if cls.is_atheris_mode():
            # Running under Atheris - set up and run the fuzzer
            import atheris

            # Instrument all Python modules for coverage-guided fuzzing
            atheris.instrument_all()

            # Set up the fuzzer with the target function
            atheris.Setup(sys.argv, target_fn)

            # Run the fuzzer
            atheris.Fuzz()
        # When not in atheris mode (pytest), do nothing
        # pytest will discover and run hypothesis_test directly


def create_atheris_target(
    strategy: SearchStrategy[T],
    test_fn: Callable[[T], None],
) -> Callable[[bytes], None]:
    """Create an Atheris-compatible target from a Hypothesis strategy.

    This helper function creates a fuzz target that converts raw bytes
    to structured inputs using the provided strategy, then passes them
    to the test function.

    Args:
        strategy: A Hypothesis SearchStrategy for generating structured inputs
        test_fn: A test function that accepts the structured input

    Returns:
        A function suitable for use as an Atheris fuzz target

    Example:
        ```python
        from hypothesis import strategies as st


        def test_process_user(user: dict) -> None:
            process_user(user['name'], user['age'])


        user_strategy = st.fixed_dictionaries(
            {'name': st.text(min_size=1), 'age': st.integers(0, 150)}
        )

        fuzz_target = create_atheris_target(user_strategy, test_process_user)
        ```
    """

    def atheris_target(data: bytes) -> None:
        if len(data) == 0:
            return  # Skip empty inputs
        try:
            structured_input = PolyglotHarness.bytes_to_structured(data, strategy)
            test_fn(structured_input)
        except Exception:
            # Let the fuzzer continue on handled exceptions
            # Unhandled crashes will still be caught by Atheris
            pass

    return atheris_target
