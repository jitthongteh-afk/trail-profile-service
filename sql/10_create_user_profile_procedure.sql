USE [Assessment1DB];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE CW2.sp_CreateUserProfile
    @Username NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;

    -- Normalize whitespace before validation.
    SET @Username = LTRIM(RTRIM(
        REPLACE(
            REPLACE(
                REPLACE(@Username, NCHAR(9), N' '),
                NCHAR(10), N' '
            ),
            NCHAR(13), N' '
        )
    ));

    IF @Username IS NULL OR LEN(@Username) = 0
    BEGIN
        ;THROW 50020, 'Username is required.', 1;
    END;

    -- NVARCHAR(50) can store up to 100 bytes.
    IF DATALENGTH(@Username) > 100
    BEGIN
        ;THROW 50021, 'Username exceeds the maximum supported length.', 1;
    END;

    BEGIN TRY
        -- RoleID defaults to Member; CreatedDate is generated automatically.
        INSERT INTO CW2.USER_PROFILE (Username)
        VALUES (@Username);
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() IN (2601, 2627)
        BEGIN
            ;THROW 50022, 'Username already exists.', 1;
        END;

        THROW;
    END CATCH;

    DECLARE @NewUserID INT =
        CONVERT(INT, SCOPE_IDENTITY());

    SELECT
        UserID,
        Username,
        RoleID,
        RoleName,
        CreatedDate
    FROM CW2.vw_UserProfile
    WHERE UserID = @NewUserID;
END;
GO

-- Test creation without permanently retaining the test profile.
BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @TestUsername NVARCHAR(50) =
        N'Test_' + CONVERT(NVARCHAR(36), NEWID());

    EXEC CW2.sp_CreateUserProfile
        @Username = @TestUsername;

    ROLLBACK TRANSACTION;

    SELECT COUNT(*) AS RemainingTestProfiles
    FROM CW2.USER_PROFILE
    WHERE Username = @TestUsername;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO