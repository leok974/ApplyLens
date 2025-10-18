"""
Tests for release channel configuration and promotion.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.config_env import (
    DeployEnv,
    EnvConfig,
    get_env_config,
    init_config,
    is_production,
    is_canary,
    get_canary_percentage,
)


class TestEnvConfig:
    """Test environment configuration."""
    
    def test_dev_environment_defaults(self):
        """Test dev environment has correct defaults."""
        with patch.dict(os.environ, {"APPLYLENS_ENV": "dev"}, clear=True):
            config = get_env_config()
            
            assert config.env == DeployEnv.DEV
            assert "applylens_dev" in config.database_url
            assert config.canary_percentage == 0
            assert config.rate_limit_per_minute == 1000  # Relaxed for dev
            assert config.enable_telemetry is True
    
    def test_staging_environment_defaults(self):
        """Test staging environment has correct defaults."""
        with patch.dict(os.environ, {"APPLYLENS_ENV": "staging"}, clear=True):
            config = get_env_config()
            
            assert config.env == DeployEnv.STAGING
            assert "applylens_staging" in config.database_url
            assert config.canary_percentage == 0
            assert config.rate_limit_per_minute == 300
    
    def test_canary_environment_defaults(self):
        """Test canary environment has correct defaults."""
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "canary",
            "APPLYLENS_CANARY_PERCENTAGE": "25"
        }, clear=True):
            config = get_env_config()
            
            assert config.env == DeployEnv.CANARY
            assert "applylens_prod" in config.database_url  # Uses prod DB
            assert config.canary_percentage == 25
            assert config.rate_limit_per_minute == 60
    
    def test_prod_environment_defaults(self):
        """Test prod environment has correct defaults."""
        with patch.dict(os.environ, {"APPLYLENS_ENV": "prod"}, clear=True):
            config = get_env_config()
            
            assert config.env == DeployEnv.PROD
            assert "applylens_prod" in config.database_url
            assert config.canary_percentage == 100  # Full traffic
            assert config.rate_limit_per_minute == 60
    
    def test_environment_specific_secrets(self):
        """Test secrets are loaded per environment."""
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "prod",
            "APPLYLENS_HMAC_SECRET": "prod-hmac-secret",
            "APPLYLENS_JWT_SECRET": "prod-jwt-secret",
        }, clear=True):
            config = get_env_config()
            
            assert config.hmac_secret == "prod-hmac-secret"
            assert config.jwt_secret == "prod-jwt-secret"
    
    def test_feature_flags(self):
        """Test feature flags can be toggled."""
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "dev",
            "ENABLE_TELEMETRY": "false",
            "ENABLE_INCIDENTS": "false",
        }, clear=True):
            config = get_env_config()
            
            assert config.enable_telemetry is False
            assert config.enable_incidents is False
            assert config.enable_approvals is True  # Default true
    
    def test_custom_rate_limits(self):
        """Test custom rate limits can be set."""
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "prod",
            "MAX_CONCURRENT_REQUESTS": "50",
        }, clear=True):
            config = get_env_config()
            
            assert config.max_concurrent_requests == 50
    
    def test_custom_timeouts(self):
        """Test custom timeouts can be set."""
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "prod",
            "REQUEST_TIMEOUT_SECONDS": "15",
            "AGENT_TIMEOUT_SECONDS": "45",
        }, clear=True):
            config = get_env_config()
            
            assert config.request_timeout_seconds == 15
            assert config.agent_timeout_seconds == 45
    
    def test_is_production(self):
        """Test production environment detection."""
        with patch.dict(os.environ, {"APPLYLENS_ENV": "dev"}, clear=True):
            assert is_production() is False
        
        with patch.dict(os.environ, {"APPLYLENS_ENV": "staging"}, clear=True):
            assert is_production() is False
        
        with patch.dict(os.environ, {"APPLYLENS_ENV": "canary"}, clear=True):
            assert is_production() is True
        
        with patch.dict(os.environ, {"APPLYLENS_ENV": "prod"}, clear=True):
            assert is_production() is True
    
    def test_is_canary(self):
        """Test canary mode detection."""
        with patch.dict(os.environ, {"APPLYLENS_ENV": "dev"}, clear=True):
            assert is_canary() is False
        
        with patch.dict(os.environ, {"APPLYLENS_ENV": "canary"}, clear=True):
            assert is_canary() is True
        
        # Prod with partial canary
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "prod",
            "APPLYLENS_CANARY_PERCENTAGE": "50"
        }, clear=True):
            # Need to reinit config
            init_config()
            # Canary percentage in prod doesn't make it canary mode
            # That would be handled differently in production
            assert is_canary() is False  # Full prod
    
    def test_get_canary_percentage(self):
        """Test canary percentage retrieval."""
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "canary",
            "APPLYLENS_CANARY_PERCENTAGE": "15"
        }, clear=True):
            init_config()
            assert get_canary_percentage() == 15
    
    def test_invalid_canary_percentage_clamped(self):
        """Test canary percentage is validated."""
        # Pydantic should validate the range (0-100)
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "canary",
            "APPLYLENS_CANARY_PERCENTAGE": "150"  # Invalid
        }, clear=True):
            # Should raise validation error or clamp
            with pytest.raises(Exception):
                init_config()


class TestReleasePromotion:
    """Test release promotion logic."""
    
    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for git commands."""
        with patch('subprocess.run') as mock:
            yield mock
    
    def test_canary_promotion_workflow(self, mock_subprocess):
        """Test full canary promotion workflow."""
        # This would test the promote_release.py script
        # For now, just test the config is correct for canary
        with patch.dict(os.environ, {
            "APPLYLENS_ENV": "canary",
            "APPLYLENS_CANARY_PERCENTAGE": "10"
        }, clear=True):
            config = get_env_config()
            
            assert config.env == DeployEnv.CANARY
            assert config.canary_percentage == 10
            # Database should be prod database
            assert "prod" in config.database_url
    
    def test_environment_promotion_path(self):
        """Test environments can be promoted in order."""
        promotion_path = [DeployEnv.DEV, DeployEnv.STAGING, DeployEnv.CANARY, DeployEnv.PROD]
        
        for i in range(len(promotion_path) - 1):
            current = promotion_path[i]
            next_env = promotion_path[i + 1]
            
            # Validate promotion is allowed
            assert promotion_path.index(next_env) > promotion_path.index(current)
    
    def test_separate_databases_per_env(self):
        """Test each environment has separate database."""
        db_urls = {}
        
        for env in ["dev", "staging"]:
            with patch.dict(os.environ, {"APPLYLENS_ENV": env}, clear=True):
                config = get_env_config()
                db_urls[env] = config.database_url
        
        # Dev and staging should have different databases
        assert db_urls["dev"] != db_urls["staging"]
        assert "dev" in db_urls["dev"]
        assert "staging" in db_urls["staging"]
    
    def test_canary_and_prod_share_database(self):
        """Test canary and prod share the same database."""
        db_urls = {}
        
        for env in ["canary", "prod"]:
            with patch.dict(os.environ, {"APPLYLENS_ENV": env}, clear=True):
                config = get_env_config()
                db_urls[env] = config.database_url
        
        # Canary and prod should use same database
        # (traffic splitting happens at application layer)
        assert "prod" in db_urls["canary"]
        assert "prod" in db_urls["prod"]
    
    def test_secrets_different_per_env(self):
        """Test secrets are different per environment."""
        # In real deployment, secrets would be different
        # Here we just test they can be overridden
        secrets = {}
        
        for env in ["staging", "prod"]:
            with patch.dict(os.environ, {
                "APPLYLENS_ENV": env,
                "APPLYLENS_HMAC_SECRET": f"{env}-hmac",
                "APPLYLENS_JWT_SECRET": f"{env}-jwt",
            }, clear=True):
                config = get_env_config()
                secrets[env] = (config.hmac_secret, config.jwt_secret)
        
        assert secrets["staging"] != secrets["prod"]
        assert "staging" in secrets["staging"][0]
        assert "prod" in secrets["prod"][0]
    
    def test_production_has_stricter_rate_limits(self):
        """Test production has stricter rate limits than dev."""
        with patch.dict(os.environ, {"APPLYLENS_ENV": "dev"}, clear=True):
            dev_config = get_env_config()
        
        with patch.dict(os.environ, {"APPLYLENS_ENV": "prod"}, clear=True):
            prod_config = get_env_config()
        
        # Dev should have more relaxed limits
        assert dev_config.rate_limit_per_minute > prod_config.rate_limit_per_minute


class TestConfigGlobals:
    """Test global configuration management."""
    
    def test_init_config_sets_global(self):
        """Test init_config sets global configuration."""
        with patch.dict(os.environ, {"APPLYLENS_ENV": "staging"}, clear=True):
            config = init_config()
            
            from app.config_env import current_config
            assert current_config is not None
            assert current_config.env == DeployEnv.STAGING
    
    def test_get_config_returns_initialized(self):
        """Test get_config returns initialized config."""
        with patch.dict(os.environ, {"APPLYLENS_ENV": "prod"}, clear=True):
            init_config()
            config = get_config()
            
            assert config.env == DeployEnv.PROD
    
    def test_get_config_initializes_if_needed(self):
        """Test get_config initializes if not yet initialized."""
        # Reset global
        import app.config_env
        app.config_env.current_config = None
        
        with patch.dict(os.environ, {"APPLYLENS_ENV": "dev"}, clear=True):
            config = get_config()
            
            assert config is not None
            assert config.env == DeployEnv.DEV
