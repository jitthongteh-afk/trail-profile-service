\# Trail Profile Service



A FastAPI microservice for the COMP2001 Trail Application. Members can view and update their profiles and manage their preferred activities. A profile also shows hiking statistics and saved trail references. The service verifies sign-in credentials through the COMP2001 authenticator and uses the local profile role to authorise requests.



GitHub username: `jitthongteh-afk`  

Docker image: `jittongte/trail-profile-service:1.0`



\## Repository structure



| Path | Purpose |

| --- | --- |

| `app/` | FastAPI application, authentication, profile operations and database access |

| `app/static/index.html` | Browser interface for the profile service |

| `sql/` | Numbered SQL Server scripts for the `CW2` schema, sample data, procedures, validation and permissions |

| `Dockerfile` | Builds the application image with Microsoft ODBC Driver 18 |

| `configure\_docker.py` | Checks the local SQL login and generates `.env.docker` |

| `.env.docker.example` | Example database settings for the container |



\## Prepare SQL Server



The application container connects to SQL Server running on the Windows host. The setup below uses Docker Desktop, SQL Server Management Studio, Python and Microsoft ODBC Driver 18 for SQL Server.



1\. Create an empty database named `Assessment1DB` in SQL Server Management Studio.

2\. Run scripts `00` through `13` from `sql/` in numerical order. These create the `CW2` schema, roles, tables, sample records, view and stored procedures.

3\. Run `14\_test\_profile\_validation.sql` to check profile validation. Run `15\_create\_user\_identity.sql` to map the sample accounts to their profiles.

4\. Enable TCP/IP for the SQL Server instance and configure a fixed TCP port. The tested port was `1433`. Enable SQL Server and Windows Authentication mode and restart the SQL Server service after changing the settings.

5\. In the server's \*\*Security → Logins\*\* folder, create a SQL Server authentication login named `profile\_service\_login` with a password of your choice. Then run `16\_grant\_docker\_access.sql` in SSMS to grant the application its database permissions.



\## Run the published image



From the repository root, run these commands in Windows Command Prompt:



```bat

python -m venv .venv

.venv\\Scripts\\activate

python -m pip install -r requirements.txt

python configure\_docker.py

```



At the prompts, enter the SQL Server TCP port and the password for `profile\_service\_login`. A successful connection creates `.env.docker` on the host. Keep this file private.



Pull the published image and check that it can read the database:



```bat

docker pull jittongte/trail-profile-service:1.0

docker run --rm --env-file .env.docker jittongte/trail-profile-service:1.0 python -m app.db

```



The database check should print `Connected to database: Assessment1DB` followed by the sample profiles. Start the web service:



```bat

docker run -d --name trail-profile-service --env-file .env.docker -p 127.0.0.1:8001:8000 jittongte/trail-profile-service:1.0

```



\## Use and verify the service



| URL | Purpose |

| --- | --- |

| http://127.0.0.1:8001/ui | Open the browser interface and sign in with a COMP2001 account |

| http://127.0.0.1:8001/docs | Explore the API using Swagger UI |

| http://127.0.0.1:8001/health/database | Check database connectivity |



To verify a profile update, sign in as a member, change the location, save it and reload the profile. The saved location should appear. To verify activity preferences, add an activity, reload the profile and confirm that it appears in the preferred activities list.

