"""
Multi-LLM Provider Integration
Supports: OpenAI (ChatGPT), Anthropic (Claude), and custom API endpoints
"""
import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = ""):
        self.api_key = api_key
        self.model = model
    
    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """Generate response from LLM"""
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """OpenAI (ChatGPT) provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        # Use provided key, or fall back to .env, or use empty string
        final_key = api_key or os.getenv("OPENAI_API_KEY") or ""
        super().__init__(final_key, model)
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key) if self.api_key else None
        except ImportError:
            self.client = None
    
    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """Generate using OpenAI API"""
        if not self.client:
            return "Error: OpenAI library not installed. Run: pip install openai"
        if not self.api_key:
            return "Error: OpenAI API key not set"
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000)
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling OpenAI: {str(e)}"

class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        # Use provided key, or fall back to .env, or use empty string
        final_key = api_key or os.getenv("ANTHROPIC_API_KEY") or ""
        super().__init__(final_key, model)
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
        except ImportError:
            self.client = None
    
    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """Generate using Anthropic API"""
        if not self.client:
            return "Error: Anthropic library not installed. Run: pip install anthropic"
        if not self.api_key:
            return "Error: Anthropic API key not set"
        
        try:
            messages = [{"role": "user", "content": prompt}]
            system = system_prompt if system_prompt else None
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 2000),
                system=system,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7)
            )
            return response.content[0].text
        except Exception as e:
            return f"Error calling Anthropic: {str(e)}"

class CustomAPIProvider(LLMProvider):
    """Custom API endpoint provider (for Manus, GenSpark, etc.)"""
    
    def __init__(self, api_key: Optional[str] = None, api_url: str = "", model: str = ""):
        super().__init__(api_key, model)
        self.api_url = api_url
        try:
            import httpx
            self.http = httpx
        except ImportError:
            self.http = None
    
    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """Generate using custom API endpoint"""
        if not self.http:
            return "Error: httpx library not installed"
        if not self.api_url:
            return "Error: API URL not configured"
        
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            payload = {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "model": self.model,
                **kwargs
            }
            
            response = self.http.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # Try common response formats
            if isinstance(data, str):
                return data
            elif isinstance(data, dict):
                return data.get("response") or data.get("text") or data.get("content") or str(data)
            else:
                return str(data)
        except Exception as e:
            return f"Error calling custom API: {str(e)}"

def get_provider(provider_name: str, config: Dict[str, Any]) -> Optional[LLMProvider]:
    """Get LLM provider instance based on name and config"""
    provider_name = provider_name.lower()
    
    if provider_name in ["openai", "chatgpt", "gpt"]:
        return OpenAIProvider(
            api_key=config.get("api_key"),  # Can be None, will use .env
            model=config.get("model", "gpt-3.5-turbo")
        )
    elif provider_name in ["anthropic", "claude"]:
        return AnthropicProvider(
            api_key=config.get("api_key"),  # Can be None, will use .env
            model=config.get("model", "claude-3-sonnet-20240229")
        )
    elif provider_name in ["custom", "manus", "genspark"]:
        return CustomAPIProvider(
            api_key=config.get("api_key"),
            api_url=config.get("api_url", ""),
            model=config.get("model", "")
        )
    else:
        return None

def generate_answer(provider_name: str, config: Dict[str, Any], 
                   query: str, context: str, system_prompt: str = "") -> str:
    """Generate answer using specified provider"""
    provider = get_provider(provider_name, config)
    if not provider:
        return f"Error: Unknown provider '{provider_name}'"
    
    # Build prompt with context
    full_prompt = f"""Based on the following context, answer the question. If the answer cannot be found in the context, say so.

Context:
{context}

Question: {query}

Answer:"""
    
    return provider.generate(full_prompt, system_prompt=system_prompt)

