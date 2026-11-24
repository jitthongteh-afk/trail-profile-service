# Trail Profile Service API

Base URL: http://127.0.0.1:8001

Interactive API documentation: http://127.0.0.1:8001/docs

## Endpoint summary

| Method | Endpoint | Purpose | Documented responses |
| --- | --- | --- | --- |
| POST | `/auth/login` | Login | 200, 401, 409, 503, 422 |
| GET | `/auth/me` | Current Identity | 200 |
| POST | `/auth/logout` | Logout | 200 |
| POST | `/profiles` | Create User Profile | 201, 401, 403, 404, 409, 422, 503 |
| GET | `/profiles/{user_id}` | Get Profile | 200, 401, 403, 404, 409, 422, 503 |
| PUT | `/profiles/{user_id}` | Update User Profile | 200, 401, 403, 404, 409, 422, 503 |
| DELETE | `/profiles/{user_id}` | Delete User Profile | 200, 401, 403, 404, 409, 422, 503 |
| POST | `/profiles/{user_id}/preferences/{activity_id}` | Add User Preference | 201, 401, 403, 404, 409, 422, 503 |
| DELETE | `/profiles/{user_id}/preferences/{activity_id}` | Remove User Preference | 200, 401, 403, 404, 409, 422, 503 |
| GET | `/` | Service Information | 200 |
| GET | `/health` | Health Check | 200 |
| GET | `/health/database` | Database Health Check | 200, 503 |
| GET | `/activities` | List Activities | 200, 503 |
