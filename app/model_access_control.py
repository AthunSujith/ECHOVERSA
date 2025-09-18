"""
Model Access Control and Licensing Management for EchoVerse
Handles gated repositories, license compliance, and access permissions
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import requests
from datetime import datetime

try:
    from .model_manager import ModelSpec, get_model_registry
except ImportError:
    from model_manager import ModelSpec, get_model_registry


class LicenseType(Enum):
    """Common license types for ML models"""
    APACHE_2_0 = "Apache-2.0"
    MIT = "MIT"
    BSD_3_CLAUSE = "BSD-3-Clause"
    GPL_3_0 = "GPL-3.0"
    CUSTOM_COMMERCIAL = "Custom-Commercial"
    CUSTOM_RESEARCH = "Custom-Research"
    LLAMA_2 = "Llama-2-Custom"
    MISTRAL = "Mistral-Custom"
    UNKNOWN = "Unknown"


@dataclass
class LicenseInfo:
    """Information about a model's license"""
    license_type: LicenseType
    commercial_use: bool
    modification_allowed: bool
    distribution_allowed: bool
    attribution_required: bool
    share_alike_required: bool
    restrictions: List[str]
    license_url: Optional[str] = None
    full_text: Optional[str] = None


@dataclass
class AccessStatus:
    """Status of access to a model repository"""
    model_name: str
    repo_id: str
    is_gated: bool
    has_access: bool
    requires_auth: bool
    access_error: Optional[str] = None
    license_accepted: bool = False
    last_checked: Optional[datetime] = None


class LicenseManager:
    """Manages license information and compliance checking"""
    
    def __init__(self):
        self.license_db = self._initialize_license_database()
    
    def _initialize_license_database(self) -> Dict[LicenseType, LicenseInfo]:
        """Initialize database of known license types"""
        return {
            LicenseType.APACHE_2_0: LicenseInfo(
                license_type=LicenseType.APACHE_2_0,
                commercial_use=True,
                modification_allowed=True,
                distribution_allowed=True,
                attribution_required=True,
                share_alike_required=False,
                restrictions=[],
                license_url="https://www.apache.org/licenses/LICENSE-2.0"
            ),
            LicenseType.MIT: LicenseInfo(
                license_type=LicenseType.MIT,
                commercial_use=True,
                modification_allowed=True,
                distribution_allowed=True,
                attribution_required=True,
                share_alike_required=False,
                restrictions=[],
                license_url="https://opensource.org/licenses/MIT"
            ),
            LicenseType.BSD_3_CLAUSE: LicenseInfo(
                license_type=LicenseType.BSD_3_CLAUSE,
                commercial_use=True,
                modification_allowed=True,
                distribution_allowed=True,
                attribution_required=True,
                share_alike_required=False,
                restrictions=["Cannot use organization name for endorsement"],
                license_url="https://opensource.org/licenses/BSD-3-Clause"
            ),
            LicenseType.GPL_3_0: LicenseInfo(
                license_type=LicenseType.GPL_3_0,
                commercial_use=True,
                modification_allowed=True,
                distribution_allowed=True,
                attribution_required=True,
                share_alike_required=True,
                restrictions=["Derivative works must use same license"],
                license_url="https://www.gnu.org/licenses/gpl-3.0.html"
            ),
            LicenseType.LLAMA_2: LicenseInfo(
                license_type=LicenseType.LLAMA_2,
                commercial_use=True,  # With restrictions
                modification_allowed=True,
                distribution_allowed=True,
                attribution_required=True,
                share_alike_required=False,
                restrictions=[
                    "Commercial use restricted for services with >700M monthly active users",
                    "Cannot use to improve other language models",
                    "Must comply with acceptable use policy"
                ],
                license_url="https://ai.meta.com/llama/license/"
            ),
            LicenseType.MISTRAL: LicenseInfo(
                license_type=LicenseType.MISTRAL,
                commercial_use=True,
                modification_allowed=True,
                distribution_allowed=False,  # Typically restricted
                attribution_required=True,
                share_alike_required=False,
                restrictions=[
                    "Commercial use may require separate agreement",
                    "Distribution restrictions may apply"
                ],
                license_url="https://mistral.ai/terms/"
            ),
            LicenseType.CUSTOM_RESEARCH: LicenseInfo(
                license_type=LicenseType.CUSTOM_RESEARCH,
                commercial_use=False,
                modification_allowed=True,
                distribution_allowed=False,
                attribution_required=True,
                share_alike_required=False,
                restrictions=["Research use only", "No commercial use"],
                license_url=None
            )
        }
    
    def get_license_info(self, license_string: str) -> LicenseInfo:
        """Get license information from license string"""
        license_string = license_string.lower().strip()
        
        # Map common license strings to types
        license_mapping = {
            "apache-2.0": LicenseType.APACHE_2_0,
            "apache 2.0": LicenseType.APACHE_2_0,
            "mit": LicenseType.MIT,
            "bsd-3-clause": LicenseType.BSD_3_CLAUSE,
            "bsd": LicenseType.BSD_3_CLAUSE,
            "gpl-3.0": LicenseType.GPL_3_0,
            "gpl": LicenseType.GPL_3_0,
            "llama": LicenseType.LLAMA_2,
            "llama-2": LicenseType.LLAMA_2,
            "mistral": LicenseType.MISTRAL,
            "research": LicenseType.CUSTOM_RESEARCH,
            "research-only": LicenseType.CUSTOM_RESEARCH
        }
        
        for key, license_type in license_mapping.items():
            if key in license_string:
                return self.license_db[license_type]
        
        # Unknown license - create conservative default
        return LicenseInfo(
            license_type=LicenseType.UNKNOWN,
            commercial_use=False,
            modification_allowed=False,
            distribution_allowed=False,
            attribution_required=True,
            share_alike_required=False,
            restrictions=["Unknown license - review required"],
            license_url=None
        )
    
    def check_license_compatibility(self, license_info: LicenseInfo, 
                                  intended_use: str = "research") -> Tuple[bool, List[str]]:
        """Check if license is compatible with intended use"""
        issues = []
        
        if intended_use.lower() == "commercial":
            if not license_info.commercial_use:
                issues.append("License does not permit commercial use")
        
        if intended_use.lower() == "distribution":
            if not license_info.distribution_allowed:
                issues.append("License does not permit distribution")
        
        # Add restriction warnings
        for restriction in license_info.restrictions:
            issues.append(f"Restriction: {restriction}")
        
        return len(issues) == 0, issues


class AccessControlManager:
    """Manages access control for gated repositories and models"""
    
    def __init__(self, config_dir: str = ".kiro/model_access"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.access_cache_file = self.config_dir / "access_cache.json"
        self.license_acceptance_file = self.config_dir / "license_acceptance.json"
        self.auth_tokens_file = self.config_dir / "auth_tokens.json"
        
        self.registry = get_model_registry()
        self.license_manager = LicenseManager()
        
        # Load cached data
        self.access_cache = self._load_access_cache()
        self.license_acceptances = self._load_license_acceptances()
        self.auth_tokens = self._load_auth_tokens()
    
    def _load_access_cache(self) -> Dict[str, AccessStatus]:
        """Load cached access status information"""
        if not self.access_cache_file.exists():
            return {}
        
        try:
            with open(self.access_cache_file, 'r') as f:
                data = json.load(f)
            
            cache = {}
            for model_name, status_data in data.items():
                cache[model_name] = AccessStatus(
                    model_name=status_data['model_name'],
                    repo_id=status_data['repo_id'],
                    is_gated=status_data['is_gated'],
                    has_access=status_data['has_access'],
                    requires_auth=status_data['requires_auth'],
                    access_error=status_data.get('access_error'),
                    license_accepted=status_data.get('license_accepted', False),
                    last_checked=datetime.fromisoformat(status_data['last_checked']) if status_data.get('last_checked') else None
                )
            
            return cache
        except Exception as e:
            print(f"Error loading access cache: {e}")
            return {}
    
    def _save_access_cache(self) -> None:
        """Save access cache to file"""
        try:
            data = {}
            for model_name, status in self.access_cache.items():
                data[model_name] = {
                    'model_name': status.model_name,
                    'repo_id': status.repo_id,
                    'is_gated': status.is_gated,
                    'has_access': status.has_access,
                    'requires_auth': status.requires_auth,
                    'access_error': status.access_error,
                    'license_accepted': status.license_accepted,
                    'last_checked': status.last_checked.isoformat() if status.last_checked else None
                }
            
            with open(self.access_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving access cache: {e}")
    
    def _load_license_acceptances(self) -> Dict[str, Dict]:
        """Load license acceptance records"""
        if not self.license_acceptance_file.exists():
            return {}
        
        try:
            with open(self.license_acceptance_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading license acceptances: {e}")
            return {}
    
    def _save_license_acceptances(self) -> None:
        """Save license acceptance records"""
        try:
            with open(self.license_acceptance_file, 'w') as f:
                json.dump(self.license_acceptances, f, indent=2)
        except Exception as e:
            print(f"Error saving license acceptances: {e}")
    
    def _load_auth_tokens(self) -> Dict[str, str]:
        """Load authentication tokens (encrypted in production)"""
        if not self.auth_tokens_file.exists():
            return {}
        
        try:
            with open(self.auth_tokens_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading auth tokens: {e}")
            return {}
    
    def _save_auth_tokens(self) -> None:
        """Save authentication tokens (should be encrypted in production)"""
        try:
            with open(self.auth_tokens_file, 'w') as f:
                json.dump(self.auth_tokens, f, indent=2)
            
            # Set restrictive permissions on auth file
            os.chmod(self.auth_tokens_file, 0o600)
        except Exception as e:
            print(f"Error saving auth tokens: {e}")
    
    def check_repository_access(self, model_name: str, force_refresh: bool = False) -> AccessStatus:
        """Check access status for a model repository"""
        model_spec = self.registry.get_model(model_name)
        if not model_spec:
            return AccessStatus(
                model_name=model_name,
                repo_id="unknown",
                is_gated=False,
                has_access=False,
                requires_auth=False,
                access_error="Model not found in registry"
            )
        
        # Check cache first
        if not force_refresh and model_name in self.access_cache:
            cached_status = self.access_cache[model_name]
            # Use cache if checked within last 24 hours
            if cached_status.last_checked and \
               (datetime.now() - cached_status.last_checked).total_seconds() < 86400:
                return cached_status
        
        # Check repository access
        status = self._check_huggingface_access(model_spec)
        
        # Update cache
        self.access_cache[model_name] = status
        self._save_access_cache()
        
        return status
    
    def _check_huggingface_access(self, model_spec: ModelSpec) -> AccessStatus:
        """Check access to Hugging Face repository"""
        try:
            # Try to access repository info
            url = f"https://huggingface.co/api/models/{model_spec.repo_id}"
            
            # Try without authentication first
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Public repository
                return AccessStatus(
                    model_name=model_spec.name,
                    repo_id=model_spec.repo_id,
                    is_gated=False,
                    has_access=True,
                    requires_auth=False,
                    last_checked=datetime.now()
                )
            elif response.status_code == 401 or response.status_code == 403:
                # Gated repository - try with authentication
                hf_token = self.auth_tokens.get('huggingface')
                if hf_token:
                    headers = {'Authorization': f'Bearer {hf_token}'}
                    auth_response = requests.get(url, headers=headers, timeout=10)
                    
                    if auth_response.status_code == 200:
                        return AccessStatus(
                            model_name=model_spec.name,
                            repo_id=model_spec.repo_id,
                            is_gated=True,
                            has_access=True,
                            requires_auth=True,
                            last_checked=datetime.now()
                        )
                
                return AccessStatus(
                    model_name=model_spec.name,
                    repo_id=model_spec.repo_id,
                    is_gated=True,
                    has_access=False,
                    requires_auth=True,
                    access_error="Authentication required or access denied",
                    last_checked=datetime.now()
                )
            else:
                return AccessStatus(
                    model_name=model_spec.name,
                    repo_id=model_spec.repo_id,
                    is_gated=False,
                    has_access=False,
                    requires_auth=False,
                    access_error=f"Repository not found or error: {response.status_code}",
                    last_checked=datetime.now()
                )
        
        except Exception as e:
            return AccessStatus(
                model_name=model_spec.name,
                repo_id=model_spec.repo_id,
                is_gated=False,
                has_access=False,
                requires_auth=False,
                access_error=f"Error checking access: {str(e)}",
                last_checked=datetime.now()
            )
    
    def set_auth_token(self, service: str, token: str) -> None:
        """Set authentication token for a service"""
        self.auth_tokens[service] = token
        self._save_auth_tokens()
        print(f"Authentication token set for {service}")
    
    def remove_auth_token(self, service: str) -> None:
        """Remove authentication token for a service"""
        if service in self.auth_tokens:
            del self.auth_tokens[service]
            self._save_auth_tokens()
            print(f"Authentication token removed for {service}")
    
    def accept_license(self, model_name: str, license_text: str = None) -> bool:
        """Record license acceptance for a model"""
        model_spec = self.registry.get_model(model_name)
        if not model_spec:
            print(f"Model {model_name} not found")
            return False
        
        license_info = self.license_manager.get_license_info(model_spec.license)
        
        # Record acceptance
        self.license_acceptances[model_name] = {
            'model_name': model_name,
            'license_type': license_info.license_type.value,
            'accepted_date': datetime.now().isoformat(),
            'license_text': license_text,
            'commercial_use': license_info.commercial_use,
            'restrictions': license_info.restrictions
        }
        
        # Update access cache
        if model_name in self.access_cache:
            self.access_cache[model_name].license_accepted = True
        
        self._save_license_acceptances()
        self._save_access_cache()
        
        print(f"License accepted for {model_name}")
        return True
    
    def check_license_acceptance(self, model_name: str) -> bool:
        """Check if license has been accepted for a model"""
        return model_name in self.license_acceptances
    
    def get_license_guidance(self, model_name: str) -> Dict[str, any]:
        """Get guidance for accessing a restricted model"""
        model_spec = self.registry.get_model(model_name)
        if not model_spec:
            return {"error": "Model not found"}
        
        access_status = self.check_repository_access(model_name)
        license_info = self.license_manager.get_license_info(model_spec.license)
        
        guidance = {
            "model_name": model_name,
            "repo_id": model_spec.repo_id,
            "is_gated": access_status.is_gated,
            "has_access": access_status.has_access,
            "license_type": license_info.license_type.value,
            "license_accepted": self.check_license_acceptance(model_name),
            "steps": []
        }
        
        if access_status.is_gated and not access_status.has_access:
            guidance["steps"].extend([
                "1. Visit the model repository on Hugging Face",
                f"2. Go to: https://huggingface.co/{model_spec.repo_id}",
                "3. Request access if required",
                "4. Set up authentication: huggingface-cli login",
                "5. Or set token manually with set_auth_token('huggingface', 'your_token')"
            ])
        
        if not self.check_license_acceptance(model_name):
            guidance["steps"].extend([
                f"6. Review license terms: {license_info.license_url or 'See repository'}",
                "7. Accept license with accept_license() method"
            ])
        
        if license_info.restrictions:
            guidance["restrictions"] = license_info.restrictions
        
        # Suggest alternatives if access is problematic
        if not access_status.has_access:
            alternatives = self._suggest_alternatives(model_spec)
            if alternatives:
                guidance["alternatives"] = alternatives
        
        return guidance
    
    def _suggest_alternatives(self, model_spec: ModelSpec) -> List[str]:
        """Suggest alternative models that are more accessible"""
        alternatives = []
        
        # Get models of same type that are not gated
        same_type_models = self.registry.get_models_by_type(model_spec.model_type)
        
        for alt_model in same_type_models:
            if alt_model.name != model_spec.name and not alt_model.gated:
                # Check if it's a reasonable alternative (similar size/capability)
                if abs(alt_model.size_gb - model_spec.size_gb) < model_spec.size_gb * 0.5:
                    alternatives.append(alt_model.name)
        
        return alternatives[:3]  # Return top 3 alternatives
    
    def generate_access_report(self) -> Dict[str, any]:
        """Generate comprehensive access report"""
        all_models = self.registry.get_all_models()
        
        report = {
            "total_models": len(all_models),
            "accessible_models": 0,
            "gated_models": 0,
            "license_accepted": 0,
            "access_issues": [],
            "model_status": {}
        }
        
        for model_name, model_spec in all_models.items():
            access_status = self.check_repository_access(model_name)
            license_accepted = self.check_license_acceptance(model_name)
            
            if access_status.has_access:
                report["accessible_models"] += 1
            
            if access_status.is_gated:
                report["gated_models"] += 1
            
            if license_accepted:
                report["license_accepted"] += 1
            
            if access_status.access_error:
                report["access_issues"].append({
                    "model": model_name,
                    "error": access_status.access_error
                })
            
            report["model_status"][model_name] = {
                "accessible": access_status.has_access,
                "gated": access_status.is_gated,
                "license_accepted": license_accepted,
                "license_type": model_spec.license
            }
        
        return report


def create_access_manager(config_dir: str = ".kiro/model_access") -> AccessControlManager:
    """Factory function to create AccessControlManager"""
    return AccessControlManager(config_dir)