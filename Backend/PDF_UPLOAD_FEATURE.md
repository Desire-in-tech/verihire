# PDF Upload — Feature Detail

## Overview

Candidate CVs can be submitted as a PDF file upload or as raw pasted
text, through the single `POST /api/candidates` endpoint. This is a merge
point in the codebase: PDF handling (`pdfplumber` extraction) is unique to
this branch's original implementation, while everything downstream of
"we have plain text" (AI extraction, rules engine, Midnight proof,
disclosure) comes from the merged candidate/job/employer model. See
[README.md](README.md) for the full system and
[ARCHITECTURE.md](ARCHITECTURE.md) for the end-to-end data flow.

## Request

```
POST /api/candidates
Content-Type: multipart/form-data

file: (PDF file) — OR — cv_text: (string)   [exactly one required]
name: (optional) string
email: (optional) string
phone: (optional) string
```

Both `name`/`email`/`phone` are collected but never returned by this
endpoint or any other until the candidate explicitly discloses them (see
`DisclosureLevel` in [README.md](README.md#5-progressive-disclosure-post-apicandidatesiddisclosejob_id)).

## Response

```json
{
  "candidate_id": "3014b969-cff3-439d-8945-219b7981a40d",
  "anonymized_ref": "PX-101",
  "cv_source": "pdf",
  "disclosure_level": "anonymous"
}
```

`cv_source` is `"pdf"` or `"text"` depending on which input mode was used.
Internally, the `CandidateProfile` stored also keeps `extracted_text` (the
raw text pdfplumber pulled out, or the `cv_text` given directly) and the
structured `extraction` — neither is exposed by this endpoint's response
model (`response_model_exclude`), since a caller only needs the
`candidate_id` + `anonymized_ref` to continue the flow.

## Processing flow

```
1. Validate input: exactly one of `file`/`cv_text` provided
2. If `file`:
   a. Validate filename ends in .pdf
   b. Read file bytes; reject if empty
   c. Validate PDF signature (starts with b"%PDF")
   d. pdfplumber extracts text from every page, joined with blank lines
   e. Reject if no text was extracted (scanned image with no text layer)
3. Call ai_client.extract_cv(text) → HTTP POST ai_service /extract
   (real Claude tool-use call, or offline keyword fallback if
   ai_service has no ANTHROPIC_API_KEY configured)
4. Store CandidateProfile: candidate_id, anonymized_ref, extraction,
   cv_source, extracted_text, disclosure_level=anonymous
5. Return the minimal response above
```

## Implementation

**`api/candidates.py`** owns both PDF extraction (`extract_text_from_pdf`,
`PDFExtractionError`) and the `create_candidate` route handler that
branches on which input was given. There is deliberately no separate
`/api/candidates/pdf` endpoint — one endpoint, one downstream flow,
regardless of input format.

## Error handling

| Condition | HTTP status | Detail |
|---|---|---|
| Neither `file` nor `cv_text` | 422 | "Provide either a PDF file or cv_text" |
| Both `file` and `cv_text` | 422 | "Provide either a PDF file or cv_text, not both" |
| Filename doesn't end `.pdf` | 422 | "File must be a PDF" |
| Empty file | 422 | "PDF file is empty" |
| Bad PDF signature | 422 | "File is not a valid PDF" |
| pdfplumber can't parse it | 422 | "Could not parse PDF: ..." |
| No text extracted | 422 | "No extractable text found in PDF (it may be a scanned image with no text layer)" |
| `ai_service` unreachable | 502 | "AI extraction service unreachable: ..." |
| `ai_service` returns unexpected shape | 502 | "AI service returned an unexpected shape: ..." |

## Usage examples

### curl
```bash
curl -X POST http://localhost:8000/api/candidates \
  -F "file=@alice_cv.pdf" -F "name=Alice Johnson" -F "email=alice@example.com"
```

### Python (requests)
```python
import requests

with open("alice_cv.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/candidates",
        files={"file": f},
        data={"name": "Alice Johnson"},
    )
    print(response.json())
```

### React
```javascript
const formData = new FormData();
formData.append("file", pdfFile); // from <input type="file" accept=".pdf">
formData.append("name", "Alice Johnson");

const response = await fetch("/api/candidates", {
  method: "POST",
  body: formData,
});
const candidate = await response.json();
```

## Testing

See [TESTING_GUIDE.md](TESTING_GUIDE.md#scenario-3-pdf-submission) for the
full scenario, and `VeriHire_API_Collection.postman_collection.json` for a
ready-made Postman request.

## Performance

Rough numbers, dominated by the `ai_service` call rather than PDF
extraction itself:

| PDF size | pdfplumber extraction | Total (extraction + AI call) |
|---|---|---|
| 1 page | ~50-100ms | dominated by ai_service latency (real Claude call: seconds; offline fallback: <50ms) |
| 5 pages | ~200-300ms | same |
| 10 pages | ~500-800ms | same |

## Limitations

- **No OCR** — a scanned-image PDF with no text layer will fail extraction (422).
- **No encrypted/password-protected PDFs** — will fail to parse.
- **One file per request** — no batch upload.
- **PDF only** — no DOCX/DOC support.

## What stays the same regardless of input mode

- ✅ Same AI extraction step, same `ExtractionResult` shape
- ✅ Same rules engine, same Midnight proof step
- ✅ Same progressive-disclosure flow
- ✅ Same response shape from every downstream endpoint
