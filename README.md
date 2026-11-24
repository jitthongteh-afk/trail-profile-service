# Trail Profile Service

The Trail Profile Service manages user profiles for the COMP2001 Trail Application. Members can view and update their profile details, manage activity preferences, and view their hiking statistics and saved trail references. Administrators can also manage other users' profiles.

The service uses FastAPI and stores profile data in the `CW2` schema of Microsoft SQL Server. The COMP2001 authenticator verifies sign-in credentials. A user with a valid authentication account can create a trail profile if their account does not already have one.

- GitHub repository: [jitthongteh-afk/trail-profile-service](https://github.com/jitthongteh-afk/trail-profile-service)
- Docker Hub image: [jittongte/trail-profile-service](https://hub.docker.com/r/jittongte/trail-profile-service), tag `1.0`

## Repository structure

| Path | Purpose |
| --- | --- |
| `app/` | FastAPI application, authentication, database access and profile operations |
| `app/static/index.html` | Browser interface for signing in, creating a profile and managing profile details |
| `sql/` | Numbered SQL Server scripts for the CW2 schema, sample data, views, stored procedures, validation and permissions |
| `init_database.py` | Initialises a fresh coursework database using the numbered SQL scripts |
| `configure_docker.py` | Checks the application SQL login and creates the local `.env.docker` configuration |
| `.env.docker.example` | Example database configuration with placeholder credentials |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Builds the application image |
| `docker-compose.yml` | Runs the published application image on local port 8001 |

## Prepare SQL Server

The tested deployment uses Docker Desktop on Windows. The application runs in a container and connects to SQL Server on the Windows host. Install Python and Microsoft ODBC Driver 18 for SQL Server on the host. Enable SQL Server authentication and TCP/IP for the target SQL Server instance. The tested TCP port is `1433`.

From the repository root, run these commands in Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python init_database.py
```

For a fresh installation, use a Windows account with permission to create a database and a SQL login. The default target is the local default SQL Server instance. To initialise a named instance such as `SQLEXPRESS`, use `python init_database.py --server localhost\SQLEXPRESS` in place of the final command above.

The initialisation script is designed to create `Assessment1DB`, run SQL scripts `00` through `16`, and display the sample profiles. If prompted to create `profile_service_login`, choose a password and keep it for the Docker configuration step. If the login already exists, use its existing password.

If `Assessment1DB` already exists, the script prints `SKIPPED` and leaves the database unchanged. This outcome confirms that the script took the existing-database path. To check that the application can read profiles from that database, run the container query below.

## Run with Docker Compose

From the repository root, configure the SQL connection:

```bat
python configure_docker.py
```

Enter the SQL Server TCP port and the password for `profile_service_login`. The script tests the connection before writing `.env.docker`. Keep this file private because it contains the local database credentials. If you already have a working configuration, press Enter at the replacement prompt to keep it.

Pull the published image, start the service and check its status:

```bat
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
```

The `profile` service should become `healthy` and show the port mapping `127.0.0.1:8001->8000/tcp`. If the first status check shows `health: starting`, wait briefly and run `docker compose ps` again.

Verify database access from inside the running container:

```bat
docker compose exec profile python -m app.db
```

On the tested database, the command printed `Connected to database: Assessment1DB` and returned Grace Hopper, Tim Berners-Lee and Ada Lovelace with their roles.

## Open the application

| Resource | Address |
| --- | --- |
| Browser interface | [Trail Profile Service](http://127.0.0.1:8001/ui) |
| Interactive API documentation | [Swagger UI](http://127.0.0.1:8001/docs) |
| Database health check | [Database health](http://127.0.0.1:8001/health/database) |

Use **Sign in** if your COMP2001 authentication account already has a trail profile. Use **Create profile** if you have valid COMP2001 credentials and need to create the profile linked to that account. The contact email displayed in the profile can be edited independently of the email used to sign in.

To stop the application, run:

```bat
docker compose down
```

Profile data is stored in SQL Server on the Windows host and persists when the application container is removed and recreated.

## API documentation and test results

- [API reference](API_DOCUMENTATION.md) lists the 13 API operations, with their HTTP methods, paths, purposes and documented response codes.
- [Test cases and results](TEST_CASES.md) records the API and deployment checks, their expected and observed outcomes, and the fresh database installation test that remains to be run.