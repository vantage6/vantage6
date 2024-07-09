import bcrypt


class HashedPassword(str):
    """
    Represents a bcrypt hashed password in string form. Used for allowing users
    to provide a hashed initial password during server setup.
    """

    def __new__(cls, value: str):
        # attempt to use provided value as a bcrypt hash as a check
        if not cls._looks_valid_bcrypt(value):
            raise ValueError("Provided value does not appear to be a valid bcrypt hash")
        return super().__new__(cls, value)

    @staticmethod
    def _looks_valid_bcrypt(value: str):
        """
        Check if the given value *looks* like a potentially valid bcrypt hash
        by attempting to check it with bcrypt.checkpw(). Also checks for hashed
        empty string.

        `bcrypt.checkpw()` will raise ValueError if the value is not a valid,
        can also raise PanicException if not enough length.

        Parameters
        ----------
        value : str
            Purported bcrypt hash

        Returns
        -------
        bool
            True if the value looks like a valid bcrypt hash. False otherwise,
            or if the empty string hashes to the given value.
        """
        try:
            # TODO: room for improvment on this minimal check, we're assuming
            # server admin knows to do this right
            empty_check = bcrypt.checkpw(b"", value.encode("utf8"))
        except ValueError:
            return False

        return not empty_check
