# Trail Profile Service API

Use the Docker Compose base URL `http://127.0.0.1:8001`. Open [Swagger UI](http://127.0.0.1:8001/docs) for the request schemas and interactive examples.

## Sign in with Postman

| Coursework account | Email | Example check |
| --- | --- | --- |
| Ada Lovelace, Member | `ada@plymouth.ac.uk` | Read her own profile, user 3 |
| Grace Hopper, Admin | `grace@plymouth.ac.uk` | Verify her administrator role, then read profile 3 |

1. Choose a seeded account and use the corresponding COMP2001 authenticator password supplied for marking. The SQL service login is a separate database credential.
2. Send `POST http://127.0.0.1:8001/auth/login`. Choose **Body → raw → JSON**. For the sample below, set the Postman variable `course_password` locally to Ada's test password.

   ```json
   {
     "email": "ada@plymouth.ac.uk",
     "password": "{{course_password}}"
   }
   ```

3. A successful login returns HTTP 200. Copy the value of `access_token`. On a new request choose **Authorization → Bearer Token** and paste the value into **Token**. Postman adds the Authorization header.
4. Send `GET http://127.0.0.1:8001/auth/me`. With Ada's session, check for user 3 and the Member role. With Grace's session, check for user 1 and the Admin role.
5. With the same authorisation, send `GET http://127.0.0.1:8001/profiles/3` to read the profile. Send `POST /auth/logout` to end the session. Sign in again after restarting the application.

## Endpoint reference

Response codes below are those listed in the application's OpenAPI endpoint summary. A protected operation can also reject an invalid session at runtime.

| Method | Endpoint | Purpose | Documented responses |
| --- | --- | --- | --- |
| POST | `/auth/login` | Verify credentials and issue a session token | 200, 401, 409, 503, 422 |
| GET | `/auth/me` | Read the current identity and role | 200 |
| POST | `/auth/logout` | End the current session | 200 |
| POST | `/profiles` | Create a profile for a verified account | 201, 401, 403, 404, 409, 422, 503 |
| GET | `/profiles/{user_id}` | Read a profile | 200, 401, 403, 404, 409, 422, 503 |
| PUT | `/profiles/{user_id}` | Update editable profile fields | 200, 401, 403, 404, 409, 422, 503 |
| DELETE | `/profiles/{user_id}` | Delete a profile | 200, 401, 403, 404, 409, 422, 503 |
| POST | `/profiles/{user_id}/preferences/{activity_id}` | Add an activity preference | 201, 401, 403, 404, 409, 422, 503 |
| DELETE | `/profiles/{user_id}/preferences/{activity_id}` | Remove an activity preference | 200, 401, 403, 404, 409, 422, 503 |
| GET | `/` | Read service information | 200 |
| GET | `/health` | Check application health | 200 |
| GET | `/health/database` | Check database availability | 200, 503 |
| GET | `/activities` | List activities | 200, 503 |

## Profile and preference examples

**Create a profile.** Send `POST /profiles` with a JSON body containing `username`, `email` and `password`. Use an existing authenticator account that has no local profile. Success returns 201 and the assigned user ID. A verified account with an existing profile returns 409. Use a disposable test profile when verifying deletion.

**Update a profile.** Send all six editable fields to `PUT /profiles/3` using an authorised session. Read the current values first and preserve the fields you intend to keep. A JSON null clears an optional field. A successful update returns 200. Read the profile again to check the stored value.

```json
{
  "username": "Ada Lovelace",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "email": "ada@plymouth.ac.uk",
  "location": "Kuala Lumpur",
  "profile_photo": null
}
```

**Change a preference.** With Ada's session, send `POST /profiles/3/preferences/2` with no request body. If the association was absent, the response is 201. Repeating it returns 409. Send `DELETE /profiles/3/preferences/2` to remove the association (200). Repeating removal returns 404.

## Interpreting errors

| Status | Recorded example |
| --- | --- |
| 401 | Invalid credentials, or an absent or expired session |
| 403 | A signed-in member attempted to change another user's profile |
| 404 | The requested activity preference did not exist |
| 409 | The verified account already had a local profile |
| 422 | The registration request omitted the required username |

The recorded 422 response included submitted input. Use dummy values for validation tests and redact credentials from evidence. See [test cases and results](TEST_CASES.md) for the recorded outcomes and installation test status.
