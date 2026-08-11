class AppError(Exception):
    def __init__(self, error: str, message: str, status_code: int = 400, **details):
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details