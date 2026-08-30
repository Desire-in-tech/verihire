"""
LMM Agent Client - CV Extraction Service

This module handles communication with the LMM Agent (Person B's service).
It can be configured with different endpoint formats, request/response schemas,
and authentication methods as Person B specifies their API.

CONFIGURATION TEMPLATE:
This file provides a template structure. Update the configuration
when Person B provides their API specifications.
"""

import httpx
from models import ExtractedCVData
from config import get_settings
from typing import Optional, Dict, Any

# ============================================================================
# CONFIGURATION TEMPLATE - UPDATE THESE WHEN PERSON B PROVIDES SPECS
# ============================================================================

class LMMAgentConfig:
    """
    Configuration template for LMM Agent service.
    
    When Person B provides their API specifications, update:
    1. ENDPOINT_URL - The URL of the LMM Agent service
    2. REQUEST_FORMAT - How to send the PDF (file, base64, binary, etc.)
    3. RESPONSE_SCHEMA - What fields are returned
    4. AUTHENTICATION - API key, bearer token, etc.
    """
    
    # ========================================================================
    # BASIC CONFIGURATION
    # ========================================================================
    
    # URL Configuration (from .env)
    # Can be: http://localhost:8888 or https://api.lmmagent.com/extract, etc.
    BASE_URL_ENV_VAR = "LMM_AGENT_URL"
    EXTRACT_ENDPOINT_PATH = "/extract"  # Update if different
    
    # ========================================================================
    # REQUEST FORMAT OPTIONS (uncomment the one Person B uses)
    # ========================================================================
    
    # OPTION 1: Send PDF as multipart file (common)
    REQUEST_FORMAT = "multipart_file"
    REQUEST_FIELD_NAME = "cv_pdf"  # Field name for PDF in form data
    
    # OPTION 2: Send PDF as base64 encoded string
    # REQUEST_FORMAT = "base64_json"
    # REQUEST_JSON_FIELD = "pdf_data"
    
    # OPTION 3: Send PDF as binary with specific content-type
    # REQUEST_FORMAT = "binary"
    # CONTENT_TYPE = "application/pdf"
    
    # OPTION 4: Custom format (uncomment and define)
    # REQUEST_FORMAT = "custom"
    
    # ========================================================================
    # RESPONSE FORMAT OPTIONS
    # ========================================================================
    
    # OPTION 1: Direct response fields (Person B returns our ExtractedCVData format)
    RESPONSE_FORMAT = "direct"  # Response has: skills, years_experience, education_level, etc.
    
    # OPTION 2: Nested response (Person B wraps data in a field)
    # RESPONSE_FORMAT = "nested"
    # RESPONSE_DATA_FIELD = "data"  # or "extracted_data", "cv_data", etc.
    
    # OPTION 3: Custom mapping (Person B uses different field names)
    # RESPONSE_FORMAT = "mapped"
    # RESPONSE_FIELD_MAPPING = {
    #     "person_b_field_name": "our_field_name",
    #     # Example:
    #     "technical_skills": "skills",
    #     "experience_years": "years_experience",
    # }
    
    # ========================================================================
    # RESPONSE FIELD SCHEMA (when format is "mapped")
    # ========================================================================
    
    # Uncomment and fill in if Person B returns different field names
    # RESPONSE_FIELD_MAPPING = {
    #     "technical_skills": "skills",
    #     "years_of_experience": "years_experience",
    #     "education": "education_level",
    #     "spoken_languages": "languages",
    #     "professional_certifications": "certifications",
    #     "profile_summary": "summary",
    # }
    
    # ========================================================================
    # AUTHENTICATION OPTIONS
    # ========================================================================
    
    # OPTION 1: No authentication
    AUTHENTICATION = "none"
    
    # OPTION 2: API Key in header
    # AUTHENTICATION = "api_key"
    # API_KEY_HEADER = "X-API-Key"  # or "Authorization", etc.
    # API_KEY_ENV_VAR = "LMM_AGENT_API_KEY"
    
    # OPTION 3: Bearer token
    # AUTHENTICATION = "bearer"
    # BEARER_TOKEN_ENV_VAR = "LMM_AGENT_BEARER_TOKEN"
    
    # OPTION 4: Basic auth
    # AUTHENTICATION = "basic"
    # BASIC_AUTH_USERNAME_ENV = "LMM_AGENT_USERNAME"
    # BASIC_AUTH_PASSWORD_ENV = "LMM_AGENT_PASSWORD"
    
    # ========================================================================
    # TIMEOUT AND RETRY SETTINGS
    # ========================================================================
    
    REQUEST_TIMEOUT = 60.0  # seconds (increase if PDFs are large)
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    # ========================================================================
    # ERROR HANDLING
    # ========================================================================
    
    # What HTTP status codes indicate success?
    SUCCESS_STATUS_CODES = [200, 201]
    
    # What to do if response doesn't match expected schema?
    STRICT_VALIDATION = True  # If True, raise error; if False, log warning


# ============================================================================
# LMM AGENT CLIENT - NO NEED TO MODIFY
# ============================================================================

class LMMAgentClient:
    """
    Flexible client for LMM Agent service that adapts to different API specs.
    
    This client automatically handles:
    - Different request formats (multipart, base64, binary, custom)
    - Different response formats (direct, nested, mapped)
    - Various authentication methods
    - Error handling and retries
    
    When Person B provides their API specs, update LMMAgentConfig above.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.config = LMMAgentConfig()
        self.base_url = getattr(self.settings, self.config.BASE_URL_ENV_VAR, "http://localhost:8888")
    
    async def extract_cv_from_pdf(
        self,
        pdf_content: bytes,
        filename: str = "cv.pdf",
        job_id: Optional[str] = None,
    ) -> ExtractedCVData:
        """
        Send PDF to LMM Agent for extraction.
        
        Args:
            pdf_content: Raw PDF file bytes
            filename: Original filename (for logging/debugging)
            
        Returns:
            ExtractedCVData with parsed CV information
            
        Raises:
            ValueError: If request fails or response is invalid
            Exception: For network/server errors
        """
        
        if not pdf_content:
            raise ValueError("PDF content is empty")
        
        endpoint_url = f"{self.base_url}{self.config.EXTRACT_ENDPOINT_PATH}"
        
        try:
            async with httpx.AsyncClient() as client:
                # Prepare request based on configured format
                if self.config.REQUEST_FORMAT == "multipart_file":
                    response = await self._send_multipart_request(
                        client, endpoint_url, pdf_content, filename, job_id
                    )
                elif self.config.REQUEST_FORMAT == "base64_json":
                    response = await self._send_base64_request(
                        client, endpoint_url, pdf_content, job_id
                    )
                elif self.config.REQUEST_FORMAT == "binary":
                    response = await self._send_binary_request(
                        client, endpoint_url, pdf_content, job_id
                    )
                else:
                    raise ValueError(f"Unknown request format: {self.config.REQUEST_FORMAT}")
                
                # Parse response based on configured format
                extracted_data = self._parse_response(response.json())
                return extracted_data
                
        except httpx.HTTPStatusError as e:
            raise ValueError(f"LMM Agent returned error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise ValueError(f"Failed to connect to LMM Agent at {endpoint_url}: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error extracting CV from PDF: {str(e)}")
    
    async def _send_multipart_request(
        self,
        client: httpx.AsyncClient,
        url: str,
        pdf_content: bytes,
        filename: str,
        job_id: Optional[str],
    ) -> httpx.Response:
        """Send PDF as multipart form data."""
        
        headers = self._get_auth_headers()
        
        files = {
            self.config.REQUEST_FIELD_NAME: (filename, pdf_content, "application/pdf")
        }

        data = {}
        if job_id:
            data["job_id"] = job_id
        
        response = await client.post(
            url,
            files=files,
            data=data,
            headers=headers,
            timeout=self.config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response
    
    async def _send_base64_request(
        self, client: httpx.AsyncClient, url: str, pdf_content: bytes, job_id: Optional[str]
    ) -> httpx.Response:
        """Send PDF as base64 encoded JSON."""
        
        import base64
        
        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/json"
        
        encoded_pdf = base64.b64encode(pdf_content).decode("utf-8")
        payload = {self.config.REQUEST_JSON_FIELD: encoded_pdf}
        if job_id:
            payload["job_id"] = job_id
        
        response = await client.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response
    
    async def _send_binary_request(
        self, client: httpx.AsyncClient, url: str, pdf_content: bytes, job_id: Optional[str]
    ) -> httpx.Response:
        """Send PDF as binary content."""
        
        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/pdf"
        
        response = await client.post(
            url,
            content=pdf_content,
            params={"job_id": job_id} if job_id else None,
            headers=headers,
            timeout=self.config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on configuration."""
        
        headers = {}
        
        if self.config.AUTHENTICATION == "none":
            pass
        
        elif self.config.AUTHENTICATION == "api_key":
            api_key = getattr(self.settings, self.config.API_KEY_ENV_VAR, "")
            if api_key:
                headers[self.config.API_KEY_HEADER] = api_key
        
        elif self.config.AUTHENTICATION == "bearer":
            token = getattr(self.settings, self.config.BEARER_TOKEN_ENV_VAR, "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        elif self.config.AUTHENTICATION == "basic":
            import base64
            username = getattr(self.settings, self.config.BASIC_AUTH_USERNAME_ENV, "")
            password = getattr(self.settings, self.config.BASIC_AUTH_PASSWORD_ENV, "")
            if username and password:
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    def _parse_response(self, response_json: Dict[str, Any]) -> ExtractedCVData:
        """Parse LMM Agent response based on configured format."""
        
        # Extract data based on response format
        if self.config.RESPONSE_FORMAT == "direct":
            data = response_json
        
        elif self.config.RESPONSE_FORMAT == "nested":
            field = self.config.RESPONSE_DATA_FIELD
            if field not in response_json:
                raise ValueError(f"Expected field '{field}' not found in response")
            data = response_json[field]
        
        elif self.config.RESPONSE_FORMAT == "mapped":
            data = {}
            mapping = self.config.RESPONSE_FIELD_MAPPING
            for person_b_field, our_field in mapping.items():
                if person_b_field in response_json:
                    data[our_field] = response_json[person_b_field]
        
        else:
            data = response_json
        
        # Validate and convert to ExtractedCVData
        try:
            extracted_data = ExtractedCVData(**data)
            return extracted_data
        except Exception as e:
            if self.config.STRICT_VALIDATION:
                raise ValueError(f"Response schema validation failed: {str(e)}")
            else:
                # Log warning and try to construct with available fields
                print(f"Warning: Response validation failed: {str(e)}")
                # Provide defaults for missing fields
                data_with_defaults = {
                    "skills": data.get("skills", []),
                    "years_experience": data.get("years_experience", 0),
                    "education_level": data.get("education_level"),
                    "languages": data.get("languages", []),
                    "certifications": data.get("certifications", []),
                    "summary": data.get("summary"),
                }
                return ExtractedCVData(**data_with_defaults)
