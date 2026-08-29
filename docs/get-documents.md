# `get_documents`

`get_documents` returns extracted text for one explicitly named CTIS document belonging to a trial with a current approved Trial Profile.

## Input

```json
{
  "analysis_id": "ana_...",
  "trial_id": "2024-500001-00-00",
  "document_name": "Clinical Trial Protocol v3",
  "part": 1
}
```

`document_name` must exactly match, case-insensitively, one value exposed in a
`filter_trials` document-category field or in one of the approved profile's six
`available_extracted_documents` arrays. One document name is accepted per call.
`part` defaults to `1`.

## Output

```json
{
  "trial_id": "2024-500001-00-00",
  "document_name": "Clinical Trial Protocol v3",
  "document_type": "protocol",
  "part": 1,
  "text": "[[PAGE 1]]\nExtracted text...",
  "next_part": 2,
  "analysis_allowance": {
    "limit": 10,
    "used": 3,
    "remaining": 7
  }
}
```

Each part is limited to 200,000 characters. Continue with the returned `next_part` until it is `null`. Parts preserve page markers inside the text. No PDF, binary, link, page count or character count is returned.

Allowance counts unique documents, not parts or calls. Additional parts and exact retries for the same document do not consume another unit. Current limits are Light 10 and Max 50.

The tool performs no download, OCR, extraction, semantic search or model work. Missing/unapproved/unextracted documents return `DOCUMENT_UNAVAILABLE`; a part after the end returns `DOCUMENT_PART_UNAVAILABLE`.
