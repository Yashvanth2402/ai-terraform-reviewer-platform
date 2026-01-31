import os
from openai import AzureOpenAI


class AzureLLMClient:
    """
    Controlled Azure OpenAI client for AI Terraform Reviewer.
    This client is:
    - Low temperature
    - Context-grounded
    - Non-decision making
    """

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        if not self.deployment:
            raise ValueError("AZURE_OPENAI_DEPLOYMENT not set")

    def explain_risk(self, system_prompt: str, user_prompt: str) -> str:
        """
        LLM is ONLY allowed to explain and reason from given facts.
        """
        response = self.client.chat.completions.create(
            model=self.deployment,
            temperature=0.1,
            max_tokens=600,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        return response.choices[0].message.content.strip()
