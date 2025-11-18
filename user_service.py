"""
User service for managing users in the database.
Handles user CRUD operations and role management.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from database import Database

logger = logging.getLogger("rag")


class UserService:
    """Service for user management operations."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create_or_update_user(
        self,
        email: str,
        name: str,
        oauth_sub: str,
        picture: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user or update existing user from OAuth.
        
        Args:
            email: User's email address
            name: User's full name
            oauth_sub: OAuth provider subject ID (Google's user ID)
            picture: Optional profile picture URL
        
        Returns:
            User record with id, email, name, role, created_at
        """
        # Check if user exists
        existing = await self.get_user_by_email(email)
        
        if existing:
            # Update existing user
            query = """
                UPDATE users
                SET name = $1, updated_at = NOW()
                WHERE email = $2
                RETURNING id, email, name, role, created_at, updated_at
            """
            user = await self.db.fetch_one(query, name, email)
            logger.info(f"Updated existing user: {email}")
        else:
            # Check if this is the first user (make them admin)
            count_query = "SELECT COUNT(*) as count FROM users"
            count_result = await self.db.fetch_one(count_query)
            user_count = count_result['count'] if count_result else 0
            
            # First user gets admin role, others get reader
            role = 'admin' if user_count == 0 else 'reader'
            
            # Create new user
            query = """
                INSERT INTO users (email, name, role)
                VALUES ($1, $2, $3)
                RETURNING id, email, name, role, created_at, updated_at
            """
            user = await self.db.fetch_one(query, email, name, role)
            logger.info(f"Created new user: {email} with role: {role}")
        
        return dict(user) if user else None
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by UUID.
        
        Args:
            user_id: User's UUID as string
        
        Returns:
            User record or None if not found
        """
        query = """
            SELECT id, email, name, role, created_at, updated_at
            FROM users
            WHERE id = $1
        """
        user = await self.db.fetch_one(query, user_id)
        return dict(user) if user else None
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email address.
        
        Args:
            email: User's email address
        
        Returns:
            User record or None if not found
        """
        query = """
            SELECT id, email, name, role, created_at, updated_at
            FROM users
            WHERE email = $1
        """
        user = await self.db.fetch_one(query, email)
        return dict(user) if user else None
    
    async def update_user_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        """
        Update a user's role (admin function).
        
        Args:
            user_id: User's UUID
            role: New role (admin, editor, reader, owner)
        
        Returns:
            Updated user record or None if not found
        """
        # Validate role
        valid_roles = ['admin', 'editor', 'reader', 'owner']
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")
        
        query = """
            UPDATE users
            SET role = $1, updated_at = NOW()
            WHERE id = $2
            RETURNING id, email, name, role, created_at, updated_at
        """
        user = await self.db.fetch_one(query, role, user_id)
        
        if user:
            logger.info(f"Updated user {user_id} role to: {role}")
        
        return dict(user) if user else None
    
    async def list_all_users(self) -> List[Dict[str, Any]]:
        """
        List all users (admin function).
        
        Returns:
            List of all user records
        """
        query = """
            SELECT id, email, name, role, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
        """
        users = await self.db.fetch_all(query)
        return [dict(user) for user in users]
    
    async def is_admin(self, user_id: str) -> bool:
        """
        Check if user has admin role.
        
        Args:
            user_id: User's UUID
        
        Returns:
            True if user is admin, False otherwise
        """
        user = await self.get_user_by_id(user_id)
        return user and user.get('role') == 'admin'


# Global instance (will be initialized with database)
_user_service: Optional[UserService] = None


def get_user_service(db: Database) -> UserService:
    """Get or create the global UserService instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService(db)
    return _user_service

