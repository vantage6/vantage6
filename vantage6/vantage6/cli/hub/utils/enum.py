from vantage6.common.enum import StrEnumBase


class AuthCredentials(StrEnumBase):
    KEYCLOAK_ADMIN_USER = ("keycloakAdminUser", "Keycloak admin username")
    KEYCLOAK_ADMIN_PASSWORD = ("keycloakAdminPassword", "Keycloak admin password")

    def __new__(cls, value: str, description: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj
