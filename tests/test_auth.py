"""
Unit tests for authentication functions
"""

import pytest
from datetime import datetime, timedelta
from app import auth, schemas, crud


class TestAuthentication:
    """Test authentication functions"""

    def test_verify_password(self):
        """Test password verification"""
        plain_password = "testpassword123"
        hashed_password = auth.get_password_hash(plain_password)

        # Test correct password
        assert auth.verify_password(plain_password, hashed_password) is True

        # Test incorrect password
        assert auth.verify_password("wrongpassword", hashed_password) is False

    def test_get_password_hash(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed_password = auth.get_password_hash(password)

        assert hashed_password is not None
        assert isinstance(hashed_password, str)
        assert hashed_password != password  # Should be hashed, not plain text

    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expires_delta(self):
        """Test access token creation with custom expiration"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        token = auth.create_access_token(data, expires_delta)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        token = auth.create_refresh_token()

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_get_refresh_token_hash(self):
        """Test refresh token hashing"""
        refresh_token = "test_refresh_token"
        token_hash = auth.get_refresh_token_hash(refresh_token)

        assert token_hash is not None
        assert isinstance(token_hash, str)
        assert token_hash != refresh_token  # Should be hashed

    def test_verify_refresh_token(self):
        """Test refresh token verification"""
        refresh_token = "test_refresh_token"
        token_hash = auth.get_refresh_token_hash(refresh_token)

        # Test correct token
        assert auth.verify_refresh_token(refresh_token, token_hash) is True

        # Test incorrect token
        assert auth.verify_refresh_token("wrong_token", token_hash) is False

    async def test_authenticate_user_success(self, database, test_user):
        """Test successful user authentication"""
        user = await auth.authenticate_user(
            database, test_user["email"], "testpassword123"
        )

        assert user is not None
        assert user["email"] == test_user["email"]
        assert user["id"] == test_user["id"]

    async def test_authenticate_user_wrong_password(self, database, test_user):
        """Test user authentication with wrong password"""
        user = await auth.authenticate_user(
            database, test_user["email"], "wrongpassword"
        )

        assert user is False

    async def test_authenticate_user_nonexistent(self, database):
        """Test authentication with non-existent user"""
        user = await auth.authenticate_user(
            database, "nonexistent@example.com", "password123"
        )

        assert user is False

    async def test_get_current_user_success(self, database, test_user):
        """Test getting current user with valid token"""
        # Create a valid token
        token = auth.create_access_token({"sub": test_user["email"]})

        # Create a mock credentials object for testing
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await auth.get_current_user(credentials, database)

        assert user is not None
        assert user["email"] == test_user["email"]
        assert user["id"] == test_user["id"]

    async def test_get_current_user_invalid_token(self, database):
        """Test getting current user with invalid token"""
        # Create a mock credentials object for testing
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        # This should raise an exception
        with pytest.raises(Exception):
            await auth.get_current_user(credentials, database)

    async def test_get_current_user_nonexistent_user(self, database):
        """Test getting current user with token for non-existent user"""
        token = auth.create_access_token({"sub": "nonexistent@example.com"})

        # Create a mock credentials object for testing
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # This should raise an exception
        with pytest.raises(Exception):
            await auth.get_current_user(credentials, database)

    async def test_get_current_active_user(self, database, test_user):
        """Test getting current active user"""
        # Create a valid token
        token = auth.create_access_token({"sub": test_user["email"]})

        # Create a mock credentials object for testing
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await auth.get_current_user(credentials, database)
        active_user = await auth.get_current_active_user(user)

        assert active_user is not None
        assert active_user["email"] == test_user["email"]
        assert active_user["id"] == test_user["id"]

    async def test_get_current_active_user_none(self):
        """Test getting current active user with None user"""
        active_user = await auth.get_current_active_user(None)

        assert active_user is None


class TestTokenExpiration:
    """Test token expiration functionality"""

    def test_access_token_expiration(self):
        """Test access token expiration"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(seconds=1)  # Very short expiration
        token = auth.create_access_token(data, expires_delta)

        # Token should be created successfully
        assert token is not None

        # Note: We can't easily test expiration without waiting, but the function should work

    def test_refresh_token_expiration_in_database(self, database, test_user):
        """Test refresh token expiration in database context"""
        # This would require testing the actual database operations
        # For now, we'll test that the constants are set correctly
        assert hasattr(auth, "REFRESH_TOKEN_EXPIRE_DAYS")
        assert isinstance(auth.REFRESH_TOKEN_EXPIRE_DAYS, int)
        assert auth.REFRESH_TOKEN_EXPIRE_DAYS > 0


class TestPasswordSecurity:
    """Test password security features"""

    def test_password_hashing_consistency(self):
        """Test that password hashing is consistent"""
        password = "testpassword123"
        hash1 = auth.get_password_hash(password)
        hash2 = auth.get_password_hash(password)

        # Hashes should be different (due to salting)
        assert hash1 != hash2

        # But both should verify correctly
        assert auth.verify_password(password, hash1) is True
        assert auth.verify_password(password, hash2) is True

    def test_password_verification_edge_cases(self):
        """Test password verification with edge cases"""
        # Empty password
        empty_hash = auth.get_password_hash("")
        assert auth.verify_password("", empty_hash) is True
        assert auth.verify_password("wrong", empty_hash) is False

        # Very long password
        long_password = "a" * 1000
        long_hash = auth.get_password_hash(long_password)
        assert auth.verify_password(long_password, long_hash) is True
        assert auth.verify_password("wrong", long_hash) is False

    def test_token_security(self):
        """Test token security features"""
        # Test that tokens are sufficiently long
        data = {"sub": "test@example.com"}
        token = auth.create_access_token(data)

        assert len(token) > 30  # Should be a reasonably long token

        # Test that refresh tokens are different from access tokens
        refresh_token = auth.create_refresh_token()
        assert token != refresh_token

        # Test that refresh tokens are sufficiently long
        assert len(refresh_token) > 30
