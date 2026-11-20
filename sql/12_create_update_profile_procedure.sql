USE [Assessment1DB];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE CW2.sp_UpdateUserProfile
    @UserID INT,
    @Username NVARCHAR(MAX),
    @FirstName NVARCHAR(MAX),
    @LastName NVARCHAR(MAX),
    @Email NVARCHAR(MAX),
    @Location NVARCHAR(MAX),
    @ProfilePhoto NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;

    IF @UserID IS NULL OR @UserID <= 0
    BEGIN
        ;THROW 50040, 'A positive UserID is required.', 1;
    END;

    -- Apply the same username normalization used during creation.
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
        ;THROW 50041, 'Username is required.', 1;
    END;

    -- Normalize optional text fields.
    SET @FirstName = NULLIF(LTRIM(RTRIM(@FirstName)), N'');
    SET @LastName = NULLIF(LTRIM(RTRIM(@LastName)), N'');
    SET @Email = NULLIF(LTRIM(RTRIM(@Email)), N'');
    SET @Location = NULLIF(LTRIM(RTRIM(@Location)), N'');
    SET @ProfilePhoto = NULLIF(LTRIM(RTRIM(@ProfilePhoto)), N'');

    -- Validate storage limits before assigning values to table columns.
    IF DATALENGTH(@Username) > 100
       OR DATALENGTH(@FirstName) > 100
       OR DATALENGTH(@LastName) > 100
       OR DATALENGTH(@Email) > 200
       OR DATALENGTH(@Location) > 200
       OR DATALENGTH(@ProfilePhoto) > 510
    BEGIN
        ;THROW 50042, 'One or more fields exceed their maximum supported length.', 1;
    END;

    BEGIN TRY
        UPDATE CW2.USER_PROFILE
        SET
            Username = @Username,
            FirstName = @FirstName,
            LastName = @LastName,
            Email = @Email,
            Location = @Location,
            ProfilePhoto = @ProfilePhoto
        WHERE UserID = @UserID;

        IF @@ROWCOUNT = 0
        BEGIN
            ;THROW 50043, 'User profile not found.', 1;
        END;
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() IN (2601, 2627)
        BEGIN
            ;THROW 50044, 'Username or email already exists.', 1;
        END;

        THROW;
    END CATCH;

    SELECT
        UserID,
        Username,
        FirstName,
        LastName,
        Email,
        Location,
        ProfilePhoto,
        RoleID,
        RoleName,
        CreatedDate
    FROM CW2.vw_UserProfile
    WHERE UserID = @UserID;
END;
GO

-- Test an update without modifying existing sample users.
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @Suffix NVARCHAR(36) =
        CONVERT(NVARCHAR(36), NEWID());

    DECLARE @OriginalUsername NVARCHAR(50) =
        N'Before_' + @Suffix;

    DECLARE @UpdatedUsername NVARCHAR(50) =
        N'After_' + @Suffix;

    DECLARE @TestEmail NVARCHAR(100) =
        @Suffix + N'@example.com';

    INSERT INTO CW2.USER_PROFILE (Username)
    VALUES (@OriginalUsername);

    DECLARE @TestUserID INT =
        CONVERT(INT, SCOPE_IDENTITY());

    -- Display the original profile.
    SELECT
        UserID,
        Username,
        FirstName,
        LastName,
        Email,
        Location,
        ProfilePhoto,
        RoleID,
        RoleName,
        CreatedDate
    FROM CW2.vw_UserProfile
    WHERE UserID = @TestUserID;

    -- Update and display the profile.
    EXEC CW2.sp_UpdateUserProfile
        @UserID = @TestUserID,
        @Username = @UpdatedUsername,
        @FirstName = N'Test',
        @LastName = N'User',
        @Email = @TestEmail,
        @Location = N'Kuala Lumpur',
        @ProfilePhoto = NULL;

    -- Undo all test changes.
    ROLLBACK TRANSACTION;

    SELECT COUNT(*) AS RemainingTestProfiles
    FROM CW2.USER_PROFILE
    WHERE UserID = @TestUserID;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO