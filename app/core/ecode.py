class Error(Exception):
    """Custom error class with code and message"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"Error({self.code}): {self.message}"

    @property
    def http_status(self) -> int:
        """Extract HTTP status code from error code"""
        return self.code // 10000
