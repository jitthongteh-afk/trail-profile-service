USE [Assessment1DB];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE CW2.sp_ReadUserProfile
    @UserID INT
AS
BEGIN
    SET NOCOUNT ON;

    IF @UserID IS NULL OR @UserID <= 0
    BEGIN
        ;THROW 50010, 'A positive UserID is required.', 1;
    END;

    IF NOT EXISTS
    (
        SELECT 1
        FROM CW2.USER_PROFILE
        WHERE UserID = @UserID
    )
    BEGIN
        ;THROW 50011, 'User profile not found.', 1;
    END;

    -- Result set 1: profile, role, and optional statistics.
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
        CreatedDate,
        TotalHikes,
        TotalDistance,
        TotalDuration
    FROM CW2.vw_UserProfile
    WHERE UserID = @UserID;

    -- Result set 2: activity preferences.
    SELECT
        a.ActivityID,
        a.ActivityName
    FROM CW2.USER_PREFERRED_ACTIVITY AS upa
    INNER JOIN CW2.ACTIVITY AS a
        ON a.ActivityID = upa.ActivityID
    WHERE upa.UserID = @UserID
    ORDER BY a.ActivityName;

    -- Result set 3: saved trail references.
    SELECT TrailID
    FROM CW2.SAVED_TRAIL
    WHERE UserID = @UserID
    ORDER BY TrailID;
END;
GO

-- Verify the procedure using Grace Hopper's profile.
EXEC CW2.sp_ReadUserProfile @UserID = 1;
GO