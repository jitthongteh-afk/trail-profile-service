USE Assessment1DB;
GO
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF SUSER_ID(N'profile_service_login') IS NULL
BEGIN
    ROLLBACK TRANSACTION;
    THROW 50080, 'Create the SQL Server login profile_service_login first.', 1;
END;

IF USER_ID(N'profile_service_login') IS NULL
    CREATE USER [profile_service_login] FOR LOGIN [profile_service_login]
        WITH DEFAULT_SCHEMA = [CW2];

IF (SELECT sid FROM sys.database_principals WHERE name = N'profile_service_login')
    <> SUSER_SID(N'profile_service_login')
BEGIN
    ROLLBACK TRANSACTION;
    THROW 50081, 'Existing database user maps to a different login. Stop and inspect.', 1;
END;

-- Direct reads used by authentication, activities, health and profile display.
GRANT SELECT ON OBJECT::CW2.USER_IDENTITY TO [profile_service_login];
GRANT SELECT ON OBJECT::CW2.USER_PROFILE TO [profile_service_login];
GRANT SELECT ON OBJECT::CW2.ROLE TO [profile_service_login];
GRANT SELECT ON OBJECT::CW2.ACTIVITY TO [profile_service_login];
GRANT SELECT ON OBJECT::CW2.vw_UserProfile TO [profile_service_login];

-- Registration binds the verified external identity to its new local profile.
GRANT INSERT ON OBJECT::CW2.USER_IDENTITY TO [profile_service_login];

-- Profile writes run through existing procedures with the same schema owner.
GRANT EXECUTE ON OBJECT::CW2.sp_ReadUserProfile TO [profile_service_login];
GRANT EXECUTE ON OBJECT::CW2.sp_CreateUserProfile TO [profile_service_login];
GRANT EXECUTE ON OBJECT::CW2.sp_UpdateUserProfile TO [profile_service_login];
GRANT EXECUTE ON OBJECT::CW2.sp_DeleteUserProfile TO [profile_service_login];
GRANT EXECUTE ON OBJECT::CW2.sp_AddUserPreference TO [profile_service_login];
GRANT EXECUTE ON OBJECT::CW2.sp_RemoveUserPreference TO [profile_service_login];

COMMIT TRANSACTION;
SELECT N'Docker database access configured.' AS Result;
GO
