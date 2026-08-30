# PDF Upload — Quick Summary

## What it is

`POST /api/candidates` accepts a candidate's CV as **either** a PDF file
upload **or** raw pasted text — not two separate endpoints, one endpoint
with two mutually-exclusive input modes.

```
POST /api/candidates
Content-Type: multipart/form-data

Exactly one of:
- file: PDF file
- cv_text: string

Plus optional:
- name, email, phone
```

## How it works

```
PDF given?
  ├─ yes → pdfplumber extracts text from every page (api/candidates.py)
  └─ no  → cv_text used directly
              │
              ▼
     ai_client.extract_cv(text)  →  ai_service POST /extract
              │
              ▼
     CandidateProfile stored, response returns candidate_id + anonymized_ref
```

## Using curl

```bash
# PDF
curl -X POST http://localhost:8000/api/candidates \
  -F "file=@your_cv.pdf" -F "name=Alex Rivera"

# Raw text
curl -X POST http://localhost:8000/api/candidates \
  -F "cv_text=4 years Python, PostgreSQL, AWS certified, Bachelor's degree." \
  -F "name=Alex Rivera"
```

## Using JavaScript/React

```javascript
const formData = new FormData();
formData.append("file", pdfFile); // from <input type="file" accept=".pdf">
formData.append("name", "Alex Rivera");

const response = await fetch("/api/candidates", {
  method: "POST",
  body: formData, // don't set Content-Type - the browser sets the multipart boundary
});
const candidate = await response.json();
// { candidate_id, anonymized_ref, cv_source: "pdf", disclosure_level: "anonymous" }
```

## Response

Both input modes return the same shape — `cv_source` tells you which path was taken:
```json
{
  "candidate_id": "3014b969-...",
  "anonymized_ref": "PX-101",
  "cv_source": "pdf",
  "disclosure_level": "anonymous"
}
```

No name, email, phone, extracted text, or structured extraction is
returned — the response is deliberately minimal.

## Error handling

| Condition | Response |
|---|---|
| Neither `file` nor `cv_text` given | 422 "Provide either a PDF file or cv_text" |
| Both given | 422 "Provide either a PDF file or cv_text, not both" |
| Filename doesn't end in `.pdf` | 422 "File must be a PDF" |
| Empty file | 422 "PDF file is empty" |
| Invalid PDF signature | 422 "File is not a valid PDF" |
| No extractable text (e.g. scanned image) | 422 "No extractable text found in PDF..." |
| `ai_service` unreachable | 502 "AI extraction service unreachable: ..." |

## What works / what doesn't

**Works**: regular text-based PDFs, multi-page PDFs, PDFs with formatted text/tables.

**Doesn't work**: encrypted/password-protected PDFs, scanned image PDFs with no text layer (no OCR), non-PDF files.

## See also

- [PDF_UPLOAD_FEATURE.md](PDF_UPLOAD_FEATURE.md) — fuller detail
- [README.md](README.md#1-candidate-registration-post-apicandidates) — candidate registration in context of the full flow
- [TESTING_GUIDE.md](TESTING_GUIDE.md#scenario-3-pdf-submission) — test scenarios
