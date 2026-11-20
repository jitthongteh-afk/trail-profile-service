USE [Assessment1DB];
GO

IF OBJECT_ID(N'CW2.SAVED_TRAIL', N'U') IS NULL
BEGIN
    CREATE TABLE CW2.SAVED_TRAIL
    (
        UserID INT NOT NULL,
        TrailID INT NOT NULL,

        CONSTRAINT PK_CW2_SAVED_TRAIL
            PRIMARY KEY (UserID, TrailID),

        CONSTRAINT FK_CW2_SAVED_TRAIL_USER
            FOREIGN KEY (UserID)
            REFERENCES CW2.USER_PROFILE (UserID)
            ON DELETE CASCADE
    );
END;
GO

SELECT UserID, TrailID
FROM CW2.SAVED_TRAIL;
GO


SELECT
    s.name AS SchemaName,
    t.name AS TableName
FROM sys.tables AS t
INNER JOIN sys.schemas AS s
    ON t.schema_id = s.schema_id
WHERE s.name = N'CW2'
ORDER BY t.name;
GO