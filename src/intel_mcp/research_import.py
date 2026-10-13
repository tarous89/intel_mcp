"""Website-only snapshot transfer. Does not create projects or repeat a search."""
import hmac
import tempfile
from pydantic import ValidationError
from starlette.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from .memory_work import json_bytes, workspace_gate, run_cpu
from .research_workspace import PreviewSpec, workspace_payload, payload_key
from .selection import SelectionError


def snapshot_endpoint(store, service_token):
    @workspace_gate(store)
    async def snapshot(request):
        supplied = request.headers.get('authorization', '')
        if not service_token or not hmac.compare_digest(supplied, 'Bearer '+service_token):
            return JSONResponse({'error': {'code': 'UNAUTHORIZED'}}, status_code=401)
        try:
            raw = await request.body()
            if len(raw) > 131072:
                return JSONResponse({'error': {'code': 'REQUEST_TOO_LARGE'}}, status_code=413)
            spec = PreviewSpec.model_validate_json(raw)
            def render():
                payload = workspace_payload(store.get(spec.selection_id), spec.title,
                                            spec.include_cro_contacts, spec.recommendations)
                if payload_key(payload) != spec.snapshot_key:
                    raise SelectionError('PREVIEW_CHANGED')
                spool = tempfile.SpooledTemporaryFile(max_size=256*1024, mode='w+b')
                try:
                    # Same bytes/options as JSONResponse, validated before response headers.
                    for chunk in json_bytes({'payload': payload}, ensure_ascii=False,
                                            allow_nan=False, separators=(',', ':')):
                        spool.write(chunk)
                    length = spool.tell()
                    spool.seek(0)
                    spool.response_length = length
                    return spool
                except BaseException:
                    spool.close()
                    raise
            spool = await run_cpu(render)
            def chunks():
                try:
                    while chunk := spool.read(65536):
                        yield chunk
                finally:
                    spool.close()
            return StreamingResponse(chunks(), media_type='application/json',
                headers={'Cache-Control': 'no-store', 'Content-Length': str(spool.response_length)}, background=BackgroundTask(spool.close))
        except (SelectionError, ValidationError):
            return JSONResponse({'error': {'code': 'PREVIEW_UNAVAILABLE'}}, status_code=410,
                                headers={'Cache-Control': 'no-store'})
    return snapshot
