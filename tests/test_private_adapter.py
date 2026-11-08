from pathlib import Path
import subprocess

import pytest
import launch


def test_missing_private_checkout_is_clear(tmp_path):
    with pytest.raises(ValueError, match='Private checkout'):
        launch.prepare_private_source(tmp_path, tmp_path / 'config.yaml')


def test_private_adapter_delegates_without_copying_source(tmp_path, monkeypatch):
    root = tmp_path / 'private'
    root.mkdir()
    bridge = root / 'viewer_bridge.py'
    bridge.write_text('# private entry point')
    config = root / 'config.yaml'
    config.write_text('private config')
    def execute(command, cwd, check):
        assert cwd == root and check is True
        assert command[1] == str(bridge)
        assert command[command.index('--config') + 1] == str(config)
        destination = Path(command[command.index('--destination') + 1])
        assert destination.is_relative_to(root / '.viewer-exports')
        (destination / 'daily').mkdir()
        (destination / 'picks.json').write_text('{}')
    monkeypatch.setattr(launch.subprocess, 'run', execute)
    destination = launch.prepare_private_source(root, config)
    assert (destination / 'picks.json').is_file()
    assert not (destination / 'viewer_bridge.py').exists()


def test_failed_strategy_call_does_not_fall_back_to_demo(tmp_path, monkeypatch):
    (tmp_path / 'viewer_bridge.py').write_text('')
    config = tmp_path / 'config.yaml'
    config.write_text('')
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(launch.subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        launch.prepare_private_source(tmp_path, config)
