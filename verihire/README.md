# 🚀 VeriHire

<p align="center">
  <img src="verihire/VeriHire_Banner.png"
</p>

<h3 align="center">
Private Credentials. Verified Hiring.
</h3>

<p align="center">
A privacy-preserving hiring platform that enables candidates and employers to verify what matters before sharing sensitive information.
</p>

---

## 📖 Overview

Today's hiring process requires candidates to disclose a significant amount of personal information long before trust has been established.

Applicants often share:

- Full Resume/CV
- Personal Contact Information
- Employment History
- Educational Records
- Certifications
- Portfolio Links

At the same time, employers face challenges involving:

- Fake credentials
- Candidate fraud
- Data privacy compliance
- Resume overload
- Sensitive data management

**VeriHire** addresses these challenges through **Mutual Verification Before Disclosure**, allowing both candidates and employers to establish trust before sharing confidential information.

---

## 🎯 Problem Statement

Traditional hiring follows this pattern:

```text
Upload CV
    ↓
Reveal Personal Information
    ↓
Trust Unknown Recruiter
    ↓
Get Evaluated
```

This creates several risks:

- Exposure of sensitive personal data
- Recruitment scams
- Unnecessary data collection
- Privacy concerns
- Compliance burdens for employers

---

## 💡 Solution

VeriHire introduces a trust-first hiring framework:

```text
Verify Employer
        ↓
Prove Qualifications
        ↓
Receive Verification
        ↓
Disclose Information Only When Necessary
```

The platform minimizes unnecessary exposure while maintaining transparency and trust throughout the hiring process.

---

## 🔐 Core Features

### ✅ Employer Verification

Before applying, candidates can verify:

- Organization Identity
- Recruiter Authenticity
- Job Posting Authorization
- Active Job Status

This reduces the risk of fraudulent job postings and recruitment scams.

---

### ✅ Private Credential Verification

Instead of sending an entire resume, candidates can prove they satisfy job requirements.

Example:

#### Required

```text
Python ≥ 3 Years
PostgreSQL Experience
AWS Certification
```

#### Employer Receives

```text
Candidate #PX-104

Python ≥ 3 Years      ✅
PostgreSQL            ✅
AWS Certification     ✅

Verified by VeriHire
```

The employer learns only what is necessary.

---

### ✅ AI-Powered Credential Extraction

AI extracts and structures candidate qualifications from unstructured documents.

Example:

```json
{
  "python_experience": 4,
  "postgresql": true,
  "aws_certified": true
}
```

Extracted Information:

- Skills
- Certifications
- Education
- Experience
- Technical Expertise

---

### ✅ Privacy-Aware Job Matching

AI analyzes:

```text
Candidate Skills
            ↓
       Matching Engine
            ↓
Job Requirements
```

While ensuring minimal data exposure.

---

### ✅ Progressive Disclosure

Candidates maintain full control of their personal information.

#### Stage 1 — Anonymous Qualification

```text
Do I qualify?
```

Result:

```text
✅ Yes
```

No personal information disclosed.

---

#### Stage 2 — Verified Candidate

Employer learns:

```text
Candidate meets requirements
```

Without receiving sensitive information.

---

#### Stage 3 — Voluntary Disclosure

Only when both parties decide to proceed:

- Name
- Contact Information
- Full Resume
- Portfolio

---

## 🏗 System Architecture

```text
                    VERIHIRE

      ┌──────────────────────────────────┐
      │                                  │
      ▼                                  ▼

 Candidate                        Employer

      │                                  │
      ▼                                  ▼

   AI Credential             AI Requirement
    Extraction                 Extraction

      │                                  │
      └──────────────┬───────────────────┘
                     ▼

          Eligibility Determination

                     ▼

            Verification Layer

                     ▼

         Privacy-Preserving Match

                     ▼

           Progressive Disclosure
```

---

## 🤖 Role of Artificial Intelligence

VeriHire uses AI for three key purposes:

### 1. Credential Extraction

Convert resumes into structured credential claims.

Example:

```text
Python Experience: 4 Years
AWS Certified: True
Database Experience: True
```

---

### 2. Job Requirement Analysis

Convert job descriptions into structured requirements.

Example:

Input:

```text
Looking for an experienced Python developer
with cloud and database experience.
```

Output:

```text
Python
Backend Development
Cloud Computing
Databases
```

---

### 3. Intelligent Matching

Match candidate qualifications against employer requirements while preserving privacy.

---

## 🔒 Privacy First Design

VeriHire follows a simple principle:

> **"Don't disclose sensitive information unless it is necessary."**

The platform avoids unnecessary sharing of:

- Full resumes
- Personal contact information
- Home addresses
- Complete employment history
- Sensitive personal data

during initial hiring stages.

---

## 🎬 Example User Journey

### Scenario 1

A candidate discovers an unknown job posting.

```text
❌ Employer Verification Unavailable
```

Recommendation:

```text
Do not share sensitive information.
```

---

### Scenario 2

The candidate discovers a verified employer.

```text
✅ Employer Verified
✅ Recruiter Verified
✅ Job Verified
```

The candidate can proceed with confidence.

---

### Scenario 3

Candidate qualification verification.

```text
Python ≥ 3 Years      ✅
Backend Experience    ✅
PostgreSQL            ✅
AWS Certification     ✅
```

No resume disclosure required.

---

### Scenario 4

Employer requests an interview.

Only now does the candidate choose to reveal:

```text
Name
Email
Phone Number
Resume
Portfolio
```

---

## 🌟 Benefits

### For Candidates

- Greater privacy
- Reduced scam exposure
- Better control over personal information
- Selective disclosure

### For Employers

- Reduced compliance burden
- Less sensitive data storage
- Faster qualification screening
- Improved trust in candidates

---

## 🚀 Future Enhancements

- Verifiable Credentials (VCs)
- University-Issued Credentials
- Employer-Issued Credentials
- Decentralized Identity (DID)
- Blockchain-Based Verification
- LinkedIn Integration
- Certification Authority Integrations
- Secure Multi-Organization Credential Exchange

---

## 🛠 Tech Stack

### Frontend

- React
- TypeScript
- Tailwind CSS

### Backend

- Node.js
- Express.js

### AI Layer

- Large Language Models
- Skill Extraction Engine
- Resume Analysis

### Verification Layer

- Zero-Knowledge Proofs (Future Scope)
- Verifiable Credentials
- Privacy-Preserving Validation

### Database

- PostgreSQL

---

## 📂 Project Structure

```text
VeriHire/
│
├── frontend/
├── backend/
├── ai-engine/
├── docs/
├── images/
│   └── verihire-banner.png
│
├── README.md
└── LICENSE
```

---

## 👥 Team

| Member | Responsibility |
|----------|---------------|
| Team Member 1 | Frontend Development |
| Team Member 2 | Backend Development |
| Team Member 3 | AI & Matching Engine |
| Team Member 4 | Verification Layer & Presentation |

---

## 🏆 Vision

VeriHire transforms hiring from:

```text
Trust Us With Everything
```

into

```text
Prove Only What Matters
```

Building a safer, more transparent, and privacy-preserving future for recruitment.

---

## 📜 License

This project is developed for educational, research, and hackathon purposes.

MIT License
