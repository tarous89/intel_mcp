import asyncio
from types import SimpleNamespace
import pytest
from intel_mcp.selection import SelectionDataset, SelectionError
from intel_mcp.selection_service import authorized_selection
from test_selection import criteria, record


class Control:
    def __init__(self, reject=False, deny_profiles=False):
        self.reject = reject
        self.deny_profiles = deny_profiles
        self.filters = []
        self.profiles = []
    async def authorize_filter_results(self, analysis_id, ids):
        self.filters.append(ids)
        if self.reject:
            raise PermissionError('owner mismatch')
        return SimpleNamespace(access=SimpleNamespace(allowed_trial_ids=ids))
    async def authorize_profiles(self, analysis_id, ids):
        self.profiles.append(ids)
        return SimpleNamespace(access=SimpleNamespace(allowed_trial_ids=[] if self.deny_profiles else ids))


class Engine:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0
    async def selection(self, request):
        self.calls += 1
        return SelectionDataset(request, self.rows)


def test_auth_before_read_and_no_partial_authorized_result():
    async def run():
        engine = Engine([record()])
        with pytest.raises(PermissionError):
            await authorized_selection(Control(reject=True), engine, 'analysis', criteria())
        assert engine.calls == 0
        with pytest.raises(SelectionError, match='ALLOWANCE_INSUFFICIENT'):
            await authorized_selection(Control(deny_profiles=True), engine, 'analysis', criteria())
    asyncio.run(run())


def test_complete_authorization_batches_and_snapshot_change_before_metering():
    async def run():
        control = Control()
        engine = Engine([record(i) for i in range(1, 124)])
        result = await authorized_selection(control, engine, 'analysis', criteria())
        assert result.summary().counts['base'] == 123
        assert [len(x) for x in control.filters] == [0, 100, 23, 0]
        assert len(control.profiles) == 13 and max(map(len, control.profiles)) == 10
        control = Control()
        with pytest.raises(SelectionError, match='SELECTION_CHANGED'):
            await authorized_selection(control, engine, 'analysis', criteria(), '0' * 64)
        assert not control.profiles and control.filters == [[]]
    asyncio.run(run())


def test_http_source_cannot_silently_change_population():
    with pytest.raises(SelectionError, match='DATABASE_REQUIRED'):
        asyncio.run(authorized_selection(Control(), object(), 'analysis', criteria()))


def test_expired_lease_after_metering_never_releases_dataset():
    class ExpiringControl(Control):
        async def authorize_filter_results(self, analysis_id, ids):
            if not ids and self.profiles:
                raise PermissionError('lease expired during cohort admission')
            return await super().authorize_filter_results(analysis_id, ids)
    control = ExpiringControl()
    with pytest.raises(PermissionError, match='lease expired'):
        asyncio.run(authorized_selection(control, Engine([record()]), 'analysis', criteria()))
    assert control.profiles  # Failure occurs at the final gate, after reads/admission.
