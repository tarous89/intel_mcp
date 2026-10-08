"""Exercise the distributable boundary and its live-contract example."""
import importlib.util
from pathlib import Path
import zipfile

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts/build_chatgpt_plugin.py'
spec = importlib.util.spec_from_file_location('plugin_build', MODULE_PATH)
plugin_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_build)


def test_package_is_reproducible_and_excludes_unlisted_files(tmp_path, monkeypatch):
    import shutil
    source = tmp_path / 'source'
    shutil.copytree(plugin_build.PACKAGE, source)
    (source / '.env').write_text('DO_NOT_DISTRIBUTE=sentinel')
    (source / 'reviewer-credentials.txt').write_text('DO_NOT_DISTRIBUTE')
    monkeypatch.setattr(plugin_build, 'PACKAGE', source)
    first = plugin_build.build(tmp_path / 'one')
    second = plugin_build.build(tmp_path / 'two')
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert set(archive.namelist()) == set(plugin_build.FILES)
        assert 'plugin.json' in archive.namelist()
        assert all(b'DO_NOT_DISTRIBUTE' not in archive.read(n) for n in archive.namelist())


def test_package_rejects_symlink_payload(tmp_path, monkeypatch):
    import shutil
    import pytest
    source = tmp_path / 'source'
    shutil.copytree(plugin_build.PACKAGE, source)
    target = tmp_path / 'secret'
    target.write_text('secret')
    (source / 'plugin.json').unlink()
    (source / 'plugin.json').symlink_to(target)
    monkeypatch.setattr(plugin_build, 'PACKAGE', source)
    with pytest.raises(ValueError, match='symlinked'):
        plugin_build.validate()
