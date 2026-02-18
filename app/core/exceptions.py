from app.core.ecode import Error

# Error code format: HTTP_STATUS * 10000 + SPECIFIC_CODE
# Example: 404 * 10000 + 1 = 4040001 (displayed as 404_0001)
# To extract HTTP status: error_code // 10000

ErrResourceNotFound = Error(4040001, "resource not found")
ErrUserNotFound = Error(4040002, "user not found")

ErrInternalError = Error(5000000, "internal error")
ErrDatabaseError = Error(5000001, "database error")
ErrUserAlreadyExists = Error(4090001, "user already exists")
ErrInvalidCredentials = Error(4010001, "invalid credentials")
