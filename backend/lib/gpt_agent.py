from openai import OpenAI

class GPTAgent:
    """Wrapper for OpenAI Chat API calls."""

    def __init__(self, model="gpt-4.1-mini", temperature=0.0):
        self.client = OpenAI()
        self.model = model
        self.opts = {"temperature": temperature}

    def run(self, prompt: str, user_context: str = "") -> str:
        response = self.client.responses.create(
            model=self.model, input = prompt, **self.opts
        )
        return response.output_text
