"""Website-only snapshot transfer. Does not create projects or repeat a search."""
import hmac
from pydantic import ValidationError
from starlette.responses import JSONResponse
from .research_workspace import PreviewSpec, workspace_payload, payload_key
from .selection import SelectionError


def snapshot_endpoint(store, service_token):
    async def snapshot(request):
        supplied = request.headers.get('authorization', '')
        if not service_token or not hmac.compare_digest(supplied, 'Bearer '+service_token):
            return JSONResponse({'error': {'code': 'UNAUTHORIZED'}}, status_code=401)
        try:
            raw = await request.body()
            if len(raw) > 131072:
                return JSONResponse({'error': {'code': 'REQUEST_TOO_LARGE'}}, status_code=413)
            spec = PreviewSpec.model_validate_json(raw)
            payload = workspace_payload(store.get(spec.selection_id), spec.title,
                                        spec.include_cro_contacts, spec.recommendations)
            if payload_key(payload) != spec.snapshot_key:
                raise SelectionError('PREVIEW_CHANGED')
            return JSONResponse({'payload': payload}, headers={'Cache-Control': 'no-store'})
        except (SelectionError, ValidationError):
            return JSONResponse({'error': {'code': 'PREVIEW_UNAVAILABLE'}}, status_code=410,
                                headers={'Cache-Control': 'no-store'})
    return snapshot
