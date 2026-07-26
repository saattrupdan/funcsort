"""Regression tests for logger and module-level variable ordering."""

from funcsort.core import sort_source


class TestLoggerRegression:
    """Regression tests for logger variable ordering issues."""

    def test_logger_before_main_constant_dependency(self):
        """Regression: logger constant must appear before main() which uses it.
        
        Bug: `logger = logging.getLogger(__name__)` was being moved to the end
        of the file, even though `main()` calls `logger.info()`.
        
        Constants that functions depend on must come BEFORE those functions
        (runtime requirement - constants must be defined before use).
        """
        code = '''
import logging

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting...")


if __name__ == "__main__":
    main()
'''
        result = sort_source(code)
        # logger must come before main (constant dependency)
        logger_idx = result.find("logger = logging.getLogger")
        main_idx = result.find("def main()")
        assert logger_idx < main_idx, \
            f"logger must be defined before main(). logger at {logger_idx}, main at {main_idx}"

    def test_main_before_functions_it_calls(self):
        """Regression: main() comes before helper functions it calls.
        
        Entry point should come first among functions for readability,
        even if it calls those functions. Python defines all functions
        at module load time, so call order doesn't matter at runtime.
        """
        code = '''
def main() -> None:
    _helper()


def _helper():
    pass
'''
        result = sort_source(code)
        # main comes before _helper (entry point first among functions)
        main_idx = result.find("def main()")
        helper_idx = result.find("def _helper()")
        assert main_idx < helper_idx, \
            f"main should come before _helper. main at {main_idx}, _helper at {helper_idx}"

    def test_logger_before_main_with_helper_function(self):
        """Regression: full scenario with logger constant and helper function.
        
        - logger (constant) must come before main (uses logger.info)
        - main (entry point) comes before _helper (called by main)
        - Result order: logger, main, _helper
        """
        code = '''
import logging

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting...")
    _helper()


def _helper():
    pass
'''
        result = sort_source(code)
        logger_idx = result.find("logger = logging.getLogger")
        main_idx = result.find("def main()")
        helper_idx = result.find("def _helper()")
        
        assert logger_idx < main_idx, \
            f"logger before main. logger at {logger_idx}, main at {main_idx}"
        assert main_idx < helper_idx, \
            f"main before _helper. main at {main_idx}, _helper at {helper_idx}"

    def test_blank_line_between_imports_and_module_level_call(self):
        """Regression: module-level statements after imports need 2 blank lines (PEP 8).
        
        Bug: `logging.basicConfig(...)` was placed directly after imports
        without the required blank line separator.
        
        PEP 8 requires 2 blank lines between imports and module-level code.
        """
        code = '''
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("test")
'''
        result = sort_source(code)
        lines = result.split('\n')
        # Find the basicConfig line
        for i, line in enumerate(lines):
            if 'basicConfig' in line:
                # Two lines before should be blank (after imports)
                assert lines[i - 1] == '', \
                    f"Expected blank line before basicConfig at line {i}, got: {repr(lines[i - 1])}"
                assert lines[i - 2] == '', \
                    f"Expected two blank lines before basicConfig at line {i}, got: {repr(lines[i - 2])}"
                # Line before blanks should be import (not blank)
                assert 'import' in lines[i - 3], \
                    f"Expected import before blanks at line {i-3}, got: {repr(lines[i - 3])}"
                break
