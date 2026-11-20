USE [Assessment1DB];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE CW2.sp_AddUserPreference
    @UserID INT,
    @ActivityID INT
AS
BEGIN
    SET NOCOUNT ON;

    IF @UserID IS NULL OR @UserID <= 0
       OR @ActivityID IS NULL OR @ActivityID <= 0
    BEGIN
        ;THROW 50050, 'Positive UserID and ActivityID values are required.', 1;
    END;

    BEGIN TRY
        INSERT INTO CW2.USER_PREFERRED_ACTIVITY (UserID, ActivityID)
        VALUES (@UserID, @ActivityID);
    END TRY
    BEGIN CATCH
        IF ERROR_NUMBER() IN (2601, 2627)
        BEGIN
            ;THROW 50051, 'This activity preference already exists.', 1;
        END;

        IF ERROR_NUMBER() = 547
        BEGIN
            ;THROW 50052, 'The user profile or activity does not exist.', 1;
        END;

        THROW;
    END CATCH;

    SELECT
        @UserID AS UserID,
        @ActivityID AS ActivityID,
        'Preference added successfully.' AS ResultMessage;
END;
GO

CREATE OR ALTER PROCEDURE CW2.sp_RemoveUserPreference
    @UserID INT,
    @ActivityID INT
AS
BEGIN
    SET NOCOUNT ON;

    IF @UserID IS NULL OR @UserID <= 0
       OR @ActivityID IS NULL OR @ActivityID <= 0
    BEGIN
        ;THROW 50053, 'Positive UserID and ActivityID values are required.', 1;
    END;

    DELETE FROM CW2.USER_PREFERRED_ACTIVITY
    WHERE UserID = @UserID
      AND ActivityID = @ActivityID;

    IF @@ROWCOUNT = 0
    BEGIN
        ;THROW 50054, 'Activity preference not found.', 1;
    END;

    SELECT
        @UserID AS UserID,
        @ActivityID AS ActivityID,
        'Preference removed successfully.' AS ResultMessage;
END;
GO

-- Test both operations using a temporary profile.
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @TestUsername NVARCHAR(50) =
        N'PrefTest_' + CONVERT(NVARCHAR(36), NEWID());

    DECLARE @HikingID INT = (
        SELECT ActivityID
        FROM CW2.ACTIVITY
        WHERE ActivityName = N'Hiking'
    );

    IF @HikingID IS NULL
    BEGIN
        ;THROW 50055, 'The Hiking activity is required for this test.', 1;
    END;

    INSERT INTO CW2.USER_PROFILE (Username)
    VALUES (@TestUsername);

    DECLARE @TestUserID INT =
        CONVERT(INT, SCOPE_IDENTITY());

    EXEC CW2.sp_AddUserPreference
        @UserID = @TestUserID,
        @ActivityID = @HikingID;

    SELECT
        'After adding' AS TestStage,
        COUNT(*) AS PreferenceCount
    FROM CW2.USER_PREFERRED_ACTIVITY
    WHERE UserID = @TestUserID;

    EXEC CW2.sp_RemoveUserPreference
        @UserID = @TestUserID,
        @ActivityID = @HikingID;

    SELECT
        'After removing' AS TestStage,
        COUNT(*) AS PreferenceCount
    FROM CW2.USER_PREFERRED_ACTIVITY
    WHERE UserID = @TestUserID;

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