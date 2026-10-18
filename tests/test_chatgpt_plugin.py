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
        assert 'skills/create-custom-view/references/custom-view-guidance.md' in archive.namelist()
        assert (source/'skills/create-custom-view/references/custom-view-guidance.md').read_text() == (MODULE_PATH.parents[1]/'src/intel_mcp/custom-view-guidance.md').read_text()
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


def test_presentation_assets_match_runtime_and_package():
    runtime=MODULE_PATH.parents[1]/'src/intel_mcp'
    refs={
        'design-patterns.md':'skills/create-custom-view/references/design-patterns.md',
        'custom-view-examples.html':'skills/create-custom-view/assets/custom-view-examples.html',
        'custom-style.md':'references/custom-style.md',
        'presentation-standard.md':'references/presentation-standard.md',
        'access-and-evidence.md':'references/access-and-evidence.md',
        'research-workflow.md':'references/research-workflow.md',
        'custom-view-guidance.md':'skills/create-custom-view/references/custom-view-guidance.md',
        'custom-view-shell.html':'skills/create-custom-view/assets/custom-view-shell.html',
    }
    for name,source in refs.items():
        assert (plugin_build.PACKAGE/source).read_bytes() == (runtime/name).read_bytes()
        assert source in plugin_build.FILES
    assert len(list((plugin_build.PACKAGE/'skills').glob('*/SKILL.md')))==5
