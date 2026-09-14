# tests/conftest.py
import pytest

# Use asyncio mode 'auto' so every async test function is run with pytest-asyncio
# without needing an explicit @pytest.mark.asyncio decorator.
# This avoids the 'coroutine was never awaited' warnings on older pytest-asyncio.
def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'asyncio: mark test as async (pytest-asyncio)'
    )
