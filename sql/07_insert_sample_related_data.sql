USE [Assessment1DB];
GO

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    -- Resolve sample user IDs.
    DECLARE @GraceID INT = (
        SELECT UserID
        FROM CW2.USER_PROFILE
        WHERE Email = N'grace@plymouth.ac.uk'
    );

    DECLARE @TimID INT = (
        SELECT UserID
        FROM CW2.USER_PROFILE
        WHERE Email = N'tim@plymouth.ac.uk'
    );

    DECLARE @AdaID INT = (
        SELECT UserID
        FROM CW2.USER_PROFILE
        WHERE Email = N'ada@plymouth.ac.uk'
    );

    IF @GraceID IS NULL OR @TimID IS NULL OR @AdaID IS NULL
    BEGIN
        ;THROW 50001, 'Required sample users are missing.', 1;
    END;

    -- Resolve activity IDs.
    DECLARE @HikingID INT = (
        SELECT ActivityID
        FROM CW2.ACTIVITY
        WHERE ActivityName = N'Hiking'
    );

    DECLARE @RunningID INT = (
        SELECT ActivityID
        FROM CW2.ACTIVITY
        WHERE ActivityName = N'Running'
    );

    DECLARE @CyclingID INT = (
        SELECT ActivityID
        FROM CW2.ACTIVITY
        WHERE ActivityName = N'Cycling'
    );

    IF @HikingID IS NULL OR @RunningID IS NULL OR @CyclingID IS NULL
    BEGIN
        ;THROW 50002, 'Required activity categories are missing.', 1;
    END;

    -- Insert demonstration statistics.
    -- Distance is measured in kilometres; duration in minutes.
    INSERT INTO CW2.USER_STATISTICS
        (UserID, TotalHikes, TotalDistance, TotalDuration)
    SELECT
        src.UserID,
        src.TotalHikes,
        src.TotalDistance,
        src.TotalDuration
    FROM
    (
        VALUES
            (@GraceID, 12, 65.50, 480),
            (@TimID,    8, 42.00, 310),
            (@AdaID,   20, 110.00, 750)
    ) AS src(UserID, TotalHikes, TotalDistance, TotalDuration)
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM CW2.USER_STATISTICS AS existing
        WHERE existing.UserID = src.UserID
    );

    -- Insert sample activity preferences.
    INSERT INTO CW2.USER_PREFERRED_ACTIVITY (UserID, ActivityID)
    SELECT src.UserID, src.ActivityID
    FROM
    (
        VALUES
            (@GraceID, @HikingID),
            (@GraceID, @CyclingID),
            (@TimID,   @HikingID),
            (@TimID,   @RunningID),
            (@AdaID,   @HikingID)
    ) AS src(UserID, ActivityID)
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM CW2.USER_PREFERRED_ACTIVITY AS existing
        WHERE existing.UserID = src.UserID
          AND existing.ActivityID = src.ActivityID
    );

    -- Insert saved trails using demonstration trail IDs.
    INSERT INTO CW2.SAVED_TRAIL (UserID, TrailID)
    SELECT src.UserID, src.TrailID
    FROM
    (
        VALUES
            (@GraceID, 101),
            (@GraceID, 105),
            (@TimID,   101),
            (@AdaID,   202)
    ) AS src(UserID, TrailID)
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM CW2.SAVED_TRAIL AS existing
        WHERE existing.UserID = src.UserID
          AND existing.TrailID = src.TrailID
    );

    COMMIT TRANSACTION;

    -- Display row counts after successful completion.
    SELECT 'USER_STATISTICS' AS TableName, COUNT(*) AS RecordCount
    FROM CW2.USER_STATISTICS
    UNION ALL
    SELECT 'USER_PREFERRED_ACTIVITY', COUNT(*)
    FROM CW2.USER_PREFERRED_ACTIVITY
    UNION ALL
    SELECT 'SAVED_TRAIL', COUNT(*)
    FROM CW2.SAVED_TRAIL;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;
GO