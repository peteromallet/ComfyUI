"""Tests for CLI progress bar rendering in run-workflow."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from comfy.client.client_types import ProgressNotification


def _make_notifications() -> list[ProgressNotification]:
    """Build a realistic sequence of progress notifications."""
    return [
        ProgressNotification("executing", {"node": "1", "prompt_id": "p1"}),
        ProgressNotification("progress", {"value": 1, "max": 4, "node": "1", "prompt_id": "p1"}),
        ProgressNotification("progress", {"value": 2, "max": 4, "node": "1", "prompt_id": "p1"}),
        ProgressNotification("progress", {"value": 3, "max": 4, "node": "1", "prompt_id": "p1"}),
        ProgressNotification("progress", {"value": 4, "max": 4, "node": "1", "prompt_id": "p1"}),
        ProgressNotification("executing", {"node": "2", "prompt_id": "p1"}),
        ProgressNotification("execution_cached", {"nodes": ["3", "4"]}),
        ProgressNotification("executing", {"node": None, "prompt_id": "p1"}),
    ]


async def _async_iter(items):
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_run_with_progress_handles_events():
    """Verify _run_with_progress processes all event types without error."""
    from comfy.entrypoints.workflow import _run_with_progress

    mock_result = MagicMock()
    mock_result.outputs = {"1": {"images": [{"filename": "test.png"}]}}

    mock_task = MagicMock()
    mock_task.progress.return_value = _async_iter(_make_notifications())
    mock_task.get = AsyncMock(return_value=mock_result)

    mock_comfy = MagicMock()
    mock_comfy.queue_with_progress.return_value = mock_task

    result = await _run_with_progress(mock_comfy, {"1": {"class_type": "KSampler"}})
    assert result is mock_result
    mock_comfy.queue_with_progress.assert_called_once()


@pytest.mark.asyncio
async def test_run_with_progress_handles_empty_progress():
    """Verify _run_with_progress works when no progress events arrive."""
    from comfy.entrypoints.workflow import _run_with_progress

    mock_result = MagicMock()
    mock_result.outputs = {}

    mock_task = MagicMock()
    mock_task.progress.return_value = _async_iter([])
    mock_task.get = AsyncMock(return_value=mock_result)

    mock_comfy = MagicMock()
    mock_comfy.queue_with_progress.return_value = mock_task

    result = await _run_with_progress(mock_comfy, {})
    assert result is mock_result


def test_run_workflows_skips_progress_when_disabled():
    """Verify progress is skipped when disable_progress is set."""
    from comfy.entrypoints.workflow import run_workflows
    from comfy.cli_args_types import Configuration

    config = Configuration()
    config.disable_progress = True
    config.workflows = []

    with patch("comfy.entrypoints.workflow.Comfy") as mock_comfy_cls:
        mock_comfy_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_comfy_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        asyncio.run(run_workflows([], configuration=config))


def test_run_workflows_skips_progress_when_not_tty():
    """Verify progress is skipped when stderr is not a TTY."""
    import os
    with patch.object(os, "isatty", return_value=False):
        from comfy.entrypoints.workflow import run_workflows
        from comfy.cli_args_types import Configuration
        config = Configuration()
        config.workflows = []
        with patch("comfy.entrypoints.workflow.Comfy") as mock_comfy_cls:
            mock_comfy_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_comfy_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            asyncio.run(run_workflows([], configuration=config))
