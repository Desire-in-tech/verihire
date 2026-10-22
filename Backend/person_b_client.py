import httpx
from models import ExtractedCVData
from config import get_settings

class PersonBClient:
    """Client for communicating with Person B's CV extraction service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.PERSON_B_SERVICE_URL
    
    async def extract_cv(self, cv_text: str) -> ExtractedCVData:
        """
        Call Person B's /extract endpoint to extract CV data.
        
        Args:
            cv_text: Raw CV text
            
        Returns:
            ExtractedCVData validated with Pydantic
            
        Raises:
            httpx.HTTPError: If the request fails
            ValueError: If response doesn't match expected schema
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/extract",
                    json={"cv_text": cv_text},
                    timeout=30.0
                )
                response.raise_for_status()
                
                # Validate response with Pydantic
                data = response.json()
                extracted_data = ExtractedCVData(**data)
                return extracted_data
                
            except httpx.HTTPError as e:
                raise Exception(f"Failed to call Person B service: {str(e)}")
            except ValueError as e:
                raise ValueError(f"Invalid response schema from Person B service: {str(e)}")
