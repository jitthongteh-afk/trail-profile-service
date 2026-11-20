USE [Assessment1DB];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE CW2.sp_DeleteUserProfile
    @UserID INT
AS
BEGIN
    SET NOCOUNT ON;

    IF @UserID IS NULL OR @UserID <= 0
    BEGIN
        ;THROW 50030, 'A positive UserID is required.', 1;
    END;

    -- Related records are removed by ON DELETE CASCADE.
    DELETE FROM CW2.USER_PROFILE
    WHERE UserID = @UserID;

    IF @@ROWCOUNT = 0
    BEGIN
        ;THROW 50031, 'User profile not found.', 1;
    END;

    SELECT
        @UserID AS DeletedUserID,
        'Profile deleted successfully.' AS ResultMessage;
END;
GO

-- Verify deletion using a temporary profile and related records.
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @TestUsername NVARCHAR(50) =
        N'DeleteTest_' + CONVERT(NVARCHAR(36), NEWID());

    DECLARE @ActivityID INT = (
        SELECT ActivityID
        FROM CW2.ACTIVITY
        WHERE ActivityName = N'Hiking'
    );

    IF @ActivityID IS NULL
    BEGIN
        ;THROW 50032, 'The Hiking activity is required for this test.', 1;
    END;

    INSERT INTO CW2.USER_PROFILE (Username)
    VALUES (@TestUsername);

    DECLARE @TestUserID INT =
        CONVERT(INT, SCOPE_IDENTITY());

    INSERT INTO CW2.USER_STATISTICS (UserID)
    VALUES (@TestUserID);

    INSERT INTO CW2.USER_PREFERRED_ACTIVITY (UserID, ActivityID)
    VALUES (@TestUserID, @ActivityID);

    INSERT INTO CW2.SAVED_TRAIL (UserID, TrailID)
    VALUES (@TestUserID, 101);

    -- Each count should be 1 before deletion.
    SELECT
        'Before deletion' AS TestStage,
        (SELECT COUNT(*) FROM CW2.USER_PROFILE
         WHERE UserID = @TestUserID) AS ProfileCount,
        (SELECT COUNT(*) FROM CW2.USER_STATISTICS
         WHERE UserID = @TestUserID) AS StatisticsCount,
        (SELECT COUNT(*) FROM CW2.USER_PREFERRED_ACTIVITY
         WHERE UserID = @TestUserID) AS PreferenceCount,
        (SELECT COUNT(*) FROM CW2.SAVED_TRAIL
         WHERE UserID = @TestUserID) AS SavedTrailCount;

    EXEC CW2.sp_DeleteUserProfile @UserID = @TestUserID;

    -- Each count should be 0 after deletion.
    SELECT
        'After deletion' AS TestStage,
        (SELECT COUNT(*) FROM CW2.USER_PROFILE
         WHERE UserID = @TestUserID) AS ProfileCount,
        (SELECT COUNT(*) FROM CW2.USER_STATISTICS
         WHERE UserID = @TestUserID) AS StatisticsCount,
        (SELECT COUNT(*) FROM CW2.USER_PREFERRED_ACTIVITY
         WHERE UserID = @TestUserID) AS PreferenceCount,
        (SELECT COUNT(*) FROM CW2.SAVED_TRAIL
         WHERE UserID = @TestUserID) AS SavedTrailCount;

    -- Undo all test changes.
    ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO