\# Trail Profile Service Test Cases



The API tests used Postman against the local service at `http://127.0.0.1:8000`.

The Docker Compose deployment was checked separately at `http://127.0.0.1:8001`.

The results below record observed responses and command output.



\## API tests



| ID | Test and input | Expected result | Observed result |

| --- | --- | --- | --- |

| API-01 | Request `GET /auth/me` with Grace Hopper's valid session. | Return the authenticated user's identity and role. | PASS. HTTP 200 returned user 1, Grace Hopper, with the Admin role. |

| API-02 | Request `GET /profiles/3` for Ada Lovelace's profile. | Return the profile and its related data. | PASS. HTTP 200 returned user 3 with the Member role, hiking statistics, Hiking as a preferred activity and saved trail 202. |

| API-03 | Send `POST /profiles/3/preferences/2` with authorised access. | Create the activity preference. | PASS. HTTP 201 returned user ID 3 and activity ID 2. |

| API-04 | Send `POST /profiles/1/preferences/4` without a valid session. | Reject the unauthenticated request. | PASS. HTTP 401 reported that authentication was required or the session had expired. |

| API-05 | Send the same request using a member session without access to profile 1. | Deny access to the other user's profile. | PASS. HTTP 403 reported insufficient permission to access the profile. |

| API-06 | Send `DELETE /profiles/3/preferences/2` while the preference exists, then repeat the request. | Remove the preference once and report it missing on the second request. | PASS. The successful deletion returned HTTP 200 with both IDs. The missing preference returned HTTP 404. |

| API-07 | Send `POST /profiles` for a verified authentication account that already has a profile. | Reject a duplicate profile for that identity. | PASS. HTTP 409 reported that the authenticated account already had a profile. |

| API-08 | Send `POST /profiles` with a username, an existing test email and an incorrect password. | Reject the credentials. | PASS. HTTP 401 returned `Invalid email or password.` |

| API-09 | Send `POST /profiles` with the username field omitted. | Identify the missing required field. | PASS. HTTP 422 identified `body.username` as required. The validation response also echoed the submitted input, including the password field. |

| API-10 | Send `POST /profiles` with a verified test identity after its existing profile mapping was removed for the test. | Create a local profile for the verified identity. | PASS. HTTP 201 created profile 29 with the Member role. |

| API-11 | Send an authorised `DELETE /profiles/29` for the temporary profile created in API-10. | Delete the specified test profile. | PASS. HTTP 200 returned `deleted\_user\_id` 29. |



\## Database and deployment tests



| ID | Test | Expected result | Observed result |

| --- | --- | --- | --- |

| DEP-01 | Pull `jittongte/trail-profile-service:1.0` from Docker Hub after pushing it. | Docker resolves the published tag to the pushed image digest. | PASS. Push and pull reported the same SHA-256 digest. Docker reported that the local image was up to date. |

| DEP-02 | Run `docker compose down`, then `docker compose up -d` and `docker compose ps`. | Compose recreates the service and publishes it on local port 8001. | PASS. The profile container became healthy and showed `127.0.0.1:8001->8000/tcp`. |

| DEP-03 | Run `docker compose exec profile python -m app.db`. | The container connects to SQL Server and can read profile data. | PASS. The command connected to `Assessment1DB` and returned Grace Hopper, Tim Berners-Lee and Ada Lovelace with their roles. |

| DEP-04 | Run `python init\_database.py` when `Assessment1DB` already exists. | Skip initialisation to protect existing coursework data. | PASS. The script reported `SKIPPED` and exited. |

| DEP-05 | Run `python init\_database.py` on a fresh SQL Server instance and query the seeded profiles. | Create the database, apply the CW2 scripts and return the sample profiles. | NOT TESTED. The recorded run used an existing database and exercised the skip path. |



\## Evaluation notes



API-04 and API-05 exercised the same endpoint under different authentication conditions. The responses distinguished an invalid session (401) from an authenticated member with insufficient permission (403).



API-09 identified a privacy issue despite passing the required-field check. A follow-up change should omit password values from validation responses. A regression test should verify that the response still identifies the missing username without returning the submitted password.



DEP-03 verified database access from inside the running application container. DEP-05 remains a separate installation test for a disposable SQL Server instance.

