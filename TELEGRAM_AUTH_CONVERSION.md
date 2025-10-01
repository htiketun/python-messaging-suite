### 1. Models

-   **TelegramAccount** (`api/models/telegram_account.py`)
    -   Added `user` ForeignKey to link accounts to Django users
    -   Maintains compatibility with existing fields

### 2. Service Layer

-   **TelethonService** (`telegram_sync/telethon_service.py`)
    -   Replaces Laravel's MadelineProtoService
    -   Uses Telethon instead of MadelineProto
    -   Manages client instances and session files
    -   Handles async operations properly

### 3. Views

-   **TelegramAuthViews** (`api/views/telegram_auth.py`)
    -   `StartLoginView`: Equivalent to `startLogin()`
    -   `CheckLoginView`: Equivalent to `checkLogin()`
    -   `SubmitPhoneView`: Equivalent to `submitPhone()`
    -   `SubmitCodeView`: Equivalent to `submitCode()`
    -   `SubmitPasswordView`: Equivalent to `submitPassword()`
    -   `SubmitSignupView`: Equivalent to `submitSignup()`

### 4. URL Patterns

-   **API Routes** (`api/urls.py`)
    -   `auth/telegram/start-login/`
    -   `auth/telegram/check-login/`
    -   `auth/telegram/submit-phone/`
    -   `auth/telegram/submit-code/`
    -   `auth/telegram/submit-password/`
    -   `auth/telegram/submit-signup/`

## Key Differences

### Laravel vs Django Implementation

| Laravel Feature  | Django Equivalent | Notes                                       |
| ---------------- | ----------------- | ------------------------------------------- |
| MadelineProto    | Telethon          | Different async library for Telegram        |
| QR Login         | Phone-based login | QR implementation requires additional setup |
| Cache::put()     | Django Cache      | Same caching concept, different API         |
| Auth::id()       | request.user.id   | Django authentication system                |
| Response::json() | Response()        | DRF Response class                          |

### Authentication Flow

1. **Start Login**: Check if already authenticated, return account status
2. **Submit Phone**: Send verification code to phone number
3. **Submit Code**: Verify SMS code, handle 2FA/signup cases
4. **Submit Password**: Handle 2FA password (if required)
5. **Submit Signup**: Complete new user registration (if required)

## Configuration

### Required Settings

Add to `settings.py`:

```python
# Telegram API Configuration
TELEGRAM_API_ID = os.environ.get('TELEGRAM_API_ID', 'your_api_id')
TELEGRAM_API_HASH = os.environ.get('TELEGRAM_API_HASH', 'your_api_hash')
TELEGRAM_SESSION_FOLDER = os.path.join(BASE_DIR, 'sessions')
```

### Environment Variables

```bash
TELEGRAM_API_ID=your_actual_api_id
TELEGRAM_API_HASH=your_actual_api_hash
```

## Usage Examples

### Start Login Process

```bash
curl -X POST "http://localhost:8000/api/auth/telegram/start-login/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

### Submit Phone Number

```bash
curl -X POST "http://localhost:8000/api/auth/telegram/submit-phone/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "account_id": "uuid-here"}'
```

### Submit Verification Code

```bash
curl -X POST "http://localhost:8000/api/auth/telegram/submit-code/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code": "12345", "account_id": "uuid-here"}'
```

## Database Migration

Run the following to update the database with the new user field:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Testing

Test the setup using the management command:

```bash
python manage.py test_telegram_auth
```

## Error Handling

The Django implementation includes comprehensive error handling:

-   Session expiration detection
-   Invalid code/password handling
-   Network error handling
-   Proper HTTP status codes
-   Detailed error messages

## Security Considerations

1. **Session Storage**: Session files are stored securely in the configured folder
2. **Cache Expiration**: Phone numbers and verification data expire after 1 hour
3. **Authentication Required**: All endpoints require valid JWT authentication
4. **User Isolation**: Each user's Telegram accounts are isolated

## Future Enhancements

1. **QR Code Login**: Implement QR code authentication like the Laravel version
2. **WebSocket Support**: Add real-time updates for login status
3. **Rate Limiting**: Add rate limiting to prevent abuse
4. **Logging**: Enhanced logging for debugging and monitoring

## Troubleshooting

### Common Issues

1. **"Module not found" errors**: Ensure all imports are correct
2. **Async issues**: Make sure async functions are properly handled
3. **Session errors**: Check TELEGRAM_API_ID and TELEGRAM_API_HASH
4. **Database errors**: Run migrations after model changes

### Debug Commands

```bash
# Test the service
python manage.py test_telegram_auth

# Check migrations
python manage.py showmigrations

# Run development server
python manage.py runserver 8888
```
