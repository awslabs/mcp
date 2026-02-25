# Auto-generated repositories
from __future__ import annotations

from base_repository import BaseRepository
from entities import EmailLookup, User


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations"""

    def __init__(self, table_name: str = 'Users'):
        super().__init__(User, table_name, 'pk', None)

    # Basic CRUD Operations (Generated)
    def create_user(self, user: User) -> User:
        """Create a new user"""
        return self.create(user)

    def get_user(self, user_id: str) -> User | None:
        """Get a user by key"""
        pk = User.build_pk_for_lookup(user_id)

        return self.get(pk, None)

    def update_user(self, user: User) -> User:
        """Update an existing user"""
        return self.update(user)

    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        pk = User.build_pk_for_lookup(user_id)
        return self.delete(pk, None)


class EmailLookupRepository(BaseRepository[EmailLookup]):
    """Repository for EmailLookup entity operations"""

    def __init__(self, table_name: str = 'EmailLookup'):
        super().__init__(EmailLookup, table_name, 'pk', None)

    # Basic CRUD Operations (Generated)
    def create_email_lookup(self, email_lookup: EmailLookup) -> EmailLookup:
        """Create a new email_lookup"""
        return self.create(email_lookup)

    def get_email_lookup(self, email: str) -> EmailLookup | None:
        """Get a email_lookup by key"""
        pk = EmailLookup.build_pk_for_lookup(email)

        return self.get(pk, None)

    def update_email_lookup(self, email_lookup: EmailLookup) -> EmailLookup:
        """Update an existing email_lookup"""
        return self.update(email_lookup)

    def delete_email_lookup(self, email: str) -> bool:
        """Delete a email_lookup"""
        pk = EmailLookup.build_pk_for_lookup(email)
        return self.delete(pk, None)
