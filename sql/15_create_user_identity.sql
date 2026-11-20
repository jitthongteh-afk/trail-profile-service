USE [Assessment1DB];
GO

SET XACT_ABORT ON;
GO

IF OBJECT_ID(N'CW2.USER_IDENTITY', N'U') IS NULL
BEGIN
    CREATE TABLE CW2.USER_IDENTITY
    (
        AuthEmail NVARCHAR(100) NOT NULL,
        UserID INT NOT NULL,

        CONSTRAINT PK_CW2_USER_IDENTITY
            PRIMARY KEY (AuthEmail),

        CONSTRAINT UQ_CW2_USER_IDENTITY_UserID
            UNIQUE (UserID),

        CONSTRAINT FK_CW2_USER_IDENTITY_USER_PROFILE
            FOREIGN KEY (UserID)
            REFERENCES CW2.USER_PROFILE (UserID)
            ON DELETE CASCADE,

        CONSTRAINT CK_CW2_USER_IDENTITY_AuthEmail
            CHECK (LEN(LTRIM(RTRIM(AuthEmail))) > 0)
    );
END;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    -- Explicit mappings for the existing course sample profiles.
    DECLARE @ExpectedMappings TABLE
    (
        AuthEmail NVARCHAR(100) NOT NULL PRIMARY KEY,
        UserID INT NOT NULL UNIQUE,
        ExpectedUsername NVARCHAR(50) NOT NULL
    );

    INSERT INTO @ExpectedMappings
        (AuthEmail, UserID, ExpectedUsername)
    VALUES
        (N'grace@plymouth.ac.uk', 1, N'Grace Hopper'),
        (N'tim@plymouth.ac.uk',   2, N'Tim Berners-Lee'),
        (N'ada@plymouth.ac.uk',   3, N'Ada Lovelace');

    -- Stop if an existing identity conflicts with the expected mapping.
    IF EXISTS
    (
        SELECT 1
        FROM @ExpectedMappings AS expected
        INNER JOIN CW2.USER_IDENTITY AS identity_record
            ON identity_record.AuthEmail = expected.AuthEmail
            OR identity_record.UserID = expected.UserID
        WHERE identity_record.AuthEmail <> expected.AuthEmail
           OR identity_record.UserID <> expected.UserID
    )
    BEGIN
        ;THROW 50060, 'An existing identity mapping conflicts with the sample configuration.', 1;
    END;

    -- Verify sample profile details before creating a new mapping.
    -- Existing mappings remain valid if editable profile details change.
    IF EXISTS
    (
        SELECT 1
        FROM @ExpectedMappings AS expected
        LEFT JOIN CW2.USER_PROFILE AS profile
            ON profile.UserID = expected.UserID
        WHERE NOT EXISTS
        (
            SELECT 1
            FROM CW2.USER_IDENTITY AS identity_record
            WHERE identity_record.AuthEmail = expected.AuthEmail
              AND identity_record.UserID = expected.UserID
        )
        AND
        (
            profile.UserID IS NULL
            OR profile.Username <> expected.ExpectedUsername
            OR profile.Email IS NULL
            OR profile.Email <> expected.AuthEmail
        )
    )
    BEGIN
        ;THROW 50061, 'Sample profile details do not match. No new identity mappings were inserted.', 1;
    END;

    INSERT INTO CW2.USER_IDENTITY (AuthEmail, UserID)
    SELECT expected.AuthEmail, expected.UserID
    FROM @ExpectedMappings AS expected
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM CW2.USER_IDENTITY AS identity_record
        WHERE identity_record.AuthEmail = expected.AuthEmail
    );

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO

SELECT
    identity_record.AuthEmail,
    profile.UserID,
    profile.Username,
    role_record.RoleName
FROM CW2.USER_IDENTITY AS identity_record
INNER JOIN CW2.USER_PROFILE AS profile
    ON profile.UserID = identity_record.UserID
INNER JOIN CW2.ROLE AS role_record
    ON role_record.RoleID = profile.RoleID
ORDER BY profile.UserID;
GO