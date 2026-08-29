"""
What this file does
--------------------
Mocks the "is this employer/job legitimate?" check from the pitch doc
(Scene 1/2 of the demo: a candidate should be able to tell a real company
apart from "UnknownCompany123" before sending any sensitive information).

For the MVP this is a small in-memory registry of "known good" company
domains, seeded with the same companies used in data/jobs_seed.json. A
domain not in the registry comes back fully unverified - which is exactly
the behavior the demo's "suspicious job" scene needs.

A real version of this would check actual domain ownership (DNS TXT
record, verified email domain, etc.) and a real recruiter/company
identity check - that's future work, not needed for the demo to make its
point.
"""

from .models import EmployerVerificationResult

# domain -> whether each individual claim is verified
_VERIFIED_REGISTRY: dict[str, dict[str, bool]] = {
    "example-technologies.com": {
        "company_identity_verified": True,
        "domain_ownership_verified": True,
        "job_posting_authorized": True,
        "recruiter_authorized": True,
    },
    "northwind-systems.com": {
        "company_identity_verified": True,
        "domain_ownership_verified": True,
        "job_posting_authorized": True,
        "recruiter_authorized": True,
    },
}


def verify_employer(company_name: str, domain: str) -> EmployerVerificationResult:
    domain = domain.lower().strip()
    record = _VERIFIED_REGISTRY.get(domain)

    if record is None:
        # Unknown domain - nothing about it is verified. This is the
        # "Employer verification unavailable, don't disclose sensitive
        # information yet" scenario from the pitch doc.
        return EmployerVerificationResult(
            company_name=company_name,
            domain=domain,
            company_identity_verified=False,
            domain_ownership_verified=False,
            job_posting_authorized=False,
            recruiter_authorized=False,
        )

    return EmployerVerificationResult(company_name=company_name, domain=domain, **record)
