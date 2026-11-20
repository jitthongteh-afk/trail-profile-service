USE [Assessment1DB];
GO

IF OBJECT_ID(N'CW2.ACTIVITY', N'U') IS NULL
BEGIN
    CREATE TABLE CW2.ACTIVITY
    (
        ActivityID INT IDENTITY(1,1) NOT NULL,
        ActivityName NVARCHAR(50) NOT NULL,

        CONSTRAINT PK_CW2_ACTIVITY
            PRIMARY KEY (ActivityID),

        CONSTRAINT UQ_CW2_ACTIVITY_ActivityName
            UNIQUE (ActivityName),

        CONSTRAINT CK_CW2_ACTIVITY_ActivityName
            CHECK (LEN(LTRIM(RTRIM(ActivityName))) > 0)
    );
END;
GO

IF OBJECT_ID(N'CW2.USER_PREFERRED_ACTIVITY', N'U') IS NULL
BEGIN
    CREATE TABLE CW2.USER_PREFERRED_ACTIVITY
    (
        UserID INT NOT NULL,
        ActivityID INT NOT NULL,

        CONSTRAINT PK_CW2_USER_PREFERRED_ACTIVITY
            PRIMARY KEY (UserID, ActivityID),

        CONSTRAINT FK_CW2_UPA_USER
            FOREIGN KEY (UserID)
            REFERENCES CW2.USER_PROFILE (UserID)
            ON DELETE CASCADE,

        CONSTRAINT FK_CW2_UPA_ACTIVITY
            FOREIGN KEY (ActivityID)
            REFERENCES CW2.ACTIVITY (ActivityID)
            ON DELETE CASCADE
    );
END;
GO

INSERT INTO CW2.ACTIVITY (ActivityName)
SELECT source.ActivityName
FROM
(
    VALUES
        (N'Hiking'),
        (N'Running'),
        (N'Cycling'),
        (N'Walking')
) AS source(ActivityName)
WHERE NOT EXISTS
(
    SELECT 1
    FROM CW2.ACTIVITY AS existing
    WHERE existing.ActivityName = source.ActivityName
);
GO


SELECT ActivityID, ActivityName
FROM CW2.ACTIVITY
ORDER BY ActivityID;

SELECT UserID, ActivityID
FROM CW2.USER_PREFERRED_ACTIVITY;
GO