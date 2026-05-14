from pydantic import BaseModel, Field
from typing import Literal, Optional

class RouterParameters(BaseModel):
    city: Optional[str] = Field(None, description="City name for weather")
    expression_or_problem: Optional[str] = Field(None, description="Math expression or word problem")
    currency: Optional[str] = Field(None, description="Target currency for exchange")
    from_currency: Optional[str] = Field(None, description="Source currency")
    to_currency: Optional[str] = Field(None, description="Target currency")
    amount: Optional[float] = Field(None, description="Amount to exchange")
    message: Optional[str] = Field(None, description="Message for chat")

class RouterOutput(BaseModel):
    intent: Literal["getWeather", "calculateMath", "getExchangeRate", "generalChat"]
    parameters: RouterParameters = Field(description="Extracted parameters relevant to the intent")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
