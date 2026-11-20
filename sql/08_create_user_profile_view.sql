USE [Assessment1DB];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER VIEW CW2.vw_UserProfile
AS
SELECT
    p.UserID,
    p.Username,
    p.FirstName,
    p.LastName,
    p.Email,
    p.Location,
    p.ProfilePhoto,
    p.RoleID,
    r.RoleName,
    p.CreatedDate,
    s.TotalHikes,
    s.TotalDistance,
    s.TotalDuration
FROM CW2.USER_PROFILE AS p
INNER JOIN CW2.ROLE AS r
    ON r.RoleID = p.RoleID
LEFT JOIN CW2.USER_STATISTICS AS s
    ON s.UserID = p.UserID;
GO

-- Verify profile details, roles, and statistics.
SELECT
    UserID,
    Username,
    RoleName,
    TotalHikes,
    TotalDistance,
    TotalDuration
FROM CW2.vw_UserProfile
ORDER BY UserID;
GO