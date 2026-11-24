## Prepare SQL Server

The profile service runs in Docker and connects to SQL Server on the Windows host. This setup uses Docker Desktop, Python and Microsoft ODBC Driver 18 for SQL Server. Enable SQL Server authentication and TCP/IP on the host instance. The tested TCP port is 1433.

From the repository root, run the following commands in Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python init_database.py
```

For a fresh installation, use a Windows account with permission to create a database and a SQL login. The script targets the default local SQL Server instance. To select a named instance, use `python init_database.py --server localhost\SQLEXPRESS`.

On a fresh instance, the script creates `Assessment1DB`, runs the numbered SQL scripts from `00` to `16`, and prints the sample profiles. If prompted, choose a password for `profile_service_login` and keep it for the next step. If that login already exists, use its existing password.

If `Assessment1DB` already exists, the script prints `SKIPPED` and makes no changes. This protects existing data. A skipped run does not verify that the existing schema is complete.

## Run with Docker Compose

From the repository root, configure the database connection and start the service:

```bat
python configure_docker.py
docker compose config --quiet
docker compose up -d
docker compose ps
docker compose exec profile python -m app.db
```

`configure_docker.py` checks the application SQL login and creates the private `.env.docker` file. When a working configuration already exists, press Enter at the replacement prompt to keep it.

Compose uses the published image `jittongte/trail-profile-service:1.0`. The database check should print `Connected to database: Assessment1DB` followed by the sample profiles. Open http://127.0.0.1:8001/ui to use the application or http://127.0.0.1:8001/docs to explore the API.

To stop the application, run `docker compose down`. SQL Server stores the profile data on the Windows host.