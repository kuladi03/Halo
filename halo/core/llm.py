from ollama import chat
from halo.utils.config_loader import config

class OllamaSession:
    def __init__(self, model=None):
        self.model = model or config.llm.model
        print(f"[OllamaSession] Using model: {self.model}")

    def query_stream(self, prompt):
        """Stream tokens as they arrive (generator)."""
        messages = [{"role": "user", "content": prompt}]
        try:
            for token in chat(model=self.model, messages=messages, stream=True):
                yield token.get("message", {}).get("content", "")
        except Exception as e:
            yield f"[Error] {str(e)}"

    def query_full(self, prompt):
        """Return full response as a string."""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = chat(model=self.model, messages=messages, stream=False)
            return response.get("message", {}).get("content", "")
        except Exception as e:
            return f"[Error] {str(e)}"

# Global persistent session for Halo
ollama_session = OllamaSession(model=config.llm.model)

def query_ollama(prompt, stream=False):
    """
    Wrapper function for querying Ollama.
    - stream=True  → returns generator
    - stream=False → returns plain string
    """
    if stream:
        return ollama_session.query_stream(prompt)
    else:
        return ollama_session.query_full(prompt)
