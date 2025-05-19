"""Authentication example.

This module provides a demonstration of the AuthProvider class in LogicLayer.
It should not be considered safe for production, as it exists only to provide
an example and to enable the debug endpoints in tesseract.

In the real world, the user should implement at least the AuthProvider.get_roles
method with the matching set of roles from the user datastore.

The user is responsible to determine which token types are allowed and how to
interpret them, how to match that information with the User datastore, and to
return the set of roles according to the case.
"""

import dataclasses
from typing import Optional

from logiclayer import AuthProvider, AuthToken, AuthTokenType


@dataclasses.dataclass
class User:
    """Sample user dataclass."""

    id: str
    name: str
    roles: set[str]


class StaticAuthProvider(AuthProvider):
    """Defines a generic auth provider to enable debugging endpoints."""

    def __init__(self, token: str) -> None:
        """Create a new instance of the class."""
        self.token = token

    def _find_user_data(self, token: Optional["AuthToken"]) -> User | None:
        if token and token.kind == AuthTokenType.SEARCHPARAM and token.value == self.token:
            return User(token.value, "admin", {"sysadmin"})

        return None

    def get_roles(self, token: Optional["AuthToken"]) -> set[str]:
        """Resolve the set of roles associated with the token provided by a request."""
        user = self._find_user_data(token)
        return user.roles if user else {"visitor"}

    def get_user(self, token: Optional["AuthToken"]) -> dict[str, str] | None:
        """Resolve user information associated with the token provided by a request."""
        user = self._find_user_data(token)
        return dataclasses.asdict(user) if dataclasses.is_dataclass(user) else None
