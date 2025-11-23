#!/usr/bin/env python3
"""
Production Environment Validator
Ensures all required secrets and configuration are present before deployment.
"""

import os
import sys
from typing import List, Tuple

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_required_env(var_name: str, allow_placeholder: bool = False) -> Tuple[bool, str]:
    """Check if an environment variable is set and not a placeholder."""
    value = os.getenv(var_name)
    
    if not value:
        return False, f"{var_name} is not set"
    
    if not allow_placeholder:
        # Check for common placeholder patterns
        placeholders = [
            "placeholder",
            "changeme",
            "your-",
            "-here",
            "sk_test_placeholder",
            "whsec_placeholder",
        ]
        
        value_lower = value.lower()
        for placeholder in placeholders:
            if placeholder in value_lower:
                return False, f"{var_name} contains placeholder value"
    
    return True, "OK"


def validate_database_url(url: str) -> Tuple[bool, str]:
    """Validate DATABASE_URL format."""
    if not url:
        return False, "DATABASE_URL not set"
    
    if not url.startswith("postgresql://"):
        return False, "DATABASE_URL must use postgresql:// scheme"
    
    if "localhost" in url or "127.0.0.1" in url:
        return False, "DATABASE_URL should not use localhost in production"
    
    return True, "OK"


def validate_stripe_keys() -> List[Tuple[str, bool, str]]:
    """Validate Stripe configuration."""
    results = []
    
    stripe_key = os.getenv("STRIPE_API_KEY", "")
    if stripe_key.startswith("sk_live_"):
        results.append(("STRIPE_API_KEY (production)", True, "Using live key"))
    elif stripe_key.startswith("sk_test_"):
        results.append(("STRIPE_API_KEY (test mode)", True, "Using test key - OK for staging"))
    else:
        results.append(("STRIPE_API_KEY", False, "Invalid or missing"))
    
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if webhook_secret.startswith("whsec_"):
        results.append(("STRIPE_WEBHOOK_SECRET", True, "Valid format"))
    else:
        results.append(("STRIPE_WEBHOOK_SECRET", False, "Invalid or missing"))
    
    # Check other Stripe vars
    for var in ["STRIPE_PRICE_ID", "STRIPE_SUCCESS_URL", "STRIPE_CANCEL_URL", "STRIPE_PORTAL_RETURN_URL"]:
        success, msg = check_required_env(var, allow_placeholder=False)
        results.append((var, success, msg))
    
    return results


def main():
    print("=" * 60)
    print("Mini-RAG Production Environment Validation")
    print("=" * 60)
    print()
    
    allow_insecure = os.getenv("ALLOW_INSECURE_DEFAULTS", "false").lower() == "true"
    
    if allow_insecure:
        print(f"{YELLOW}⚠️  ALLOW_INSECURE_DEFAULTS=true - validation relaxed{RESET}")
        print(f"{YELLOW}⚠️  DO NOT use this in production!{RESET}")
        print()
    
    all_passed = True
    
    # 1. Core Authentication
    print("🔐 Authentication")
    for var in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SECRET_KEY"]:
        success, msg = check_required_env(var, allow_placeholder=allow_insecure)
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"  {status} {var}: {msg}")
        all_passed = all_passed and success
    print()
    
    # 2. Database
    print("🗄️  Database")
    db_url = os.getenv("DATABASE_URL", "")
    if allow_insecure and not db_url:
        print(f"  {YELLOW}⚠{RESET} DATABASE_URL: Skipped (allow_insecure=true)")
    else:
        success, msg = validate_database_url(db_url)
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"  {status} DATABASE_URL: {msg}")
        all_passed = all_passed and success
    print()
    
    # 3. Stripe Billing
    print("💳 Stripe Billing")
    stripe_results = validate_stripe_keys()
    for var, success, msg in stripe_results:
        if allow_insecure and not success:
            print(f"  {YELLOW}⚠{RESET} {var}: {msg} (skipped)")
        else:
            status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
            print(f"  {status} {var}: {msg}")
            all_passed = all_passed and success
    print()
    
    # 4. LLM Providers (at least one required)
    print("🤖 LLM Providers")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    
    has_openai = openai_key.startswith("sk-")
    has_anthropic = anthropic_key.startswith("sk-ant-")
    
    if has_openai:
        print(f"  {GREEN}✓{RESET} OPENAI_API_KEY: Set")
    else:
        print(f"  {YELLOW}⚠{RESET} OPENAI_API_KEY: Not set")
    
    if has_anthropic:
        print(f"  {GREEN}✓{RESET} ANTHROPIC_API_KEY: Set")
    else:
        print(f"  {YELLOW}⚠{RESET} ANTHROPIC_API_KEY: Not set")
    
    if not (has_openai or has_anthropic):
        print(f"  {RED}✗{RESET} At least one LLM provider required")
        all_passed = False
    print()
    
    # 5. Optional Features
    print("⚙️  Optional Features")
    optional_vars = {
        "BACKGROUND_JOBS_ENABLED": "Background job queue",
        "CORS_ALLOW_ORIGINS": "CORS configuration",
        "OTEL_ENABLED": "OpenTelemetry tracing",
        "OTEL_SERVICE_NAME": "Service name for traces"
    }
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  {GREEN}✓{RESET} {var}: {description} enabled")
        else:
            print(f"  {YELLOW}⚠{RESET} {var}: {description} (not configured)")
    print()
    
    # Summary
    print("=" * 60)
    if all_passed:
        print(f"{GREEN}✅ All validation checks passed!{RESET}")
        print()
        print("Ready for deployment. Run:")
        print("  docker-compose up --build")
        print()
        sys.exit(0)
    else:
        print(f"{RED}❌ Validation failed!{RESET}")
        print()
        print("Fix the errors above before deploying.")
        print()
        if not allow_insecure:
            print("For local development only, you can bypass with:")
            print("  export ALLOW_INSECURE_DEFAULTS=true")
            print("  python3 scripts/validate_production_env.py")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()

