from typing import Optional, Dict, Any, Tuple
import yaml
from .providers.ollama import OllamaProvider
from .providers.lm_studio import LMStudioProvider
from .providers.gpt4all import GPT4AllProvider
from .config.settings import Settings
from .providers.base import AIResponse
from .utils.validator import ResponseValidator, ValidationResult
from .utils.liquidity import LiquidityManager

class UniversalAI:
    def __init__(self, provider_name: Optional[str] = None):
        self.settings = Settings()
        self.provider_name = provider_name or self.settings.default_provider
        self.provider = self._init_provider(self.provider_name)
        self.validator = ResponseValidator()
        self.liquidity = LiquidityManager()

    def _init_provider(self, name: str):
        config = self.settings.get_provider_config(name)
        if name == "ollama":
            return OllamaProvider(
                host=config.get("host", "localhost"),
                port=config.get("port", 11434),
                default_model=config.get("default_model", "gemma3:latest")
            )
        elif name == "lm_studio":
            return LMStudioProvider(
                host=config.get("host", "localhost"),
                port=config.get("port", 1234),
                default_model=config.get("default_model")
            )
        elif name == "gpt4all":
            return GPT4AllProvider(
                host=config.get("host", "localhost"),
                port=config.get("port", 4891),
                default_model=config.get("default_model", "mistral-7b-instruct")
            )
        raise ValueError(f"Provider {name} not implemented yet")

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        return self.provider.generate(prompt, **kwargs)

    def run_validated_prompt(self, template_path: str, variables: Dict[str, Any]) -> Tuple[AIResponse, ValidationResult]:
        """Loads prompt, fills variables (including liquidity), generates response, and validates it"""
        
        # Inject Liquidity Calculations
        if "goal_amount" in variables:
            liq_data = self.liquidity.calculate_split(variables["goal_amount"])
            debt_fmt = f"{liq_data['debt_resolution']:.2f}".replace('.00', '')
            variables.update({
                "liq_transparent_total": f"{liq_data['transparent_total']:.2f}".replace('.00', ''),
                "liq_debt_resolution": debt_fmt,
                "liq_fees": f"{liq_data['transaction_fees']:.2f}".replace('.00', ''),
                "liq_public_note": self.liquidity.get_public_context(variables["goal_amount"])
            })

        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split template from config
        parts = content.split("### Validation Configuration")
        template = parts[0].strip()
        
        # Extract instructions section only for prompt
        # We assume the section starts with '### Instructions'
        instructions_parts = template.split("### Instructions")
        if len(instructions_parts) > 1:
            prompt_text = instructions_parts[-1].strip()
        else:
            prompt_text = template # Fallback
            
        formatted_prompt = prompt_text.format(**variables)
        
        response = self.generate(formatted_prompt)
        
        # Load rules
        rules = {}
        if len(parts) > 1:
            rules = yaml.safe_load(parts[1])
        
        # Replace variables in rules
        processed_rules = self._process_rules(rules, variables)
        
        validation = self.validator.validate(response, processed_rules)
        return response, validation

    def _process_rules(self, rules: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Replaces {var} in rules with actual values"""
        rules_str = yaml.dump(rules)
        for k, v in variables.items():
            rules_str = rules_str.replace(f"{{{k}}}", str(v))
        return yaml.safe_load(rules_str)
