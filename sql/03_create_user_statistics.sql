USE [Assessment1DB];
GO

IF OBJECT_ID(N'CW2.USER_STATISTICS', N'U') IS NULL
BEGIN
    CREATE TABLE CW2.USER_STATISTICS
    (
        UserID INT NOT NULL,

        TotalHikes INT NOT NULL
            CONSTRAINT DF_CW2_USER_STATISTICS_TotalHikes
            DEFAULT (0),

        TotalDistance DECIMAL(10,2) NOT NULL
            CONSTRAINT DF_CW2_USER_STATISTICS_TotalDistance
            DEFAULT (0),

        TotalDuration INT NOT NULL
            CONSTRAINT DF_CW2_USER_STATISTICS_TotalDuration
            DEFAULT (0),

        CONSTRAINT PK_CW2_USER_STATISTICS
            PRIMARY KEY (UserID),

        CONSTRAINT FK_CW2_USER_STATISTICS_USER
            FOREIGN KEY (UserID)
            REFERENCES CW2.USER_PROFILE (UserID)
            ON DELETE CASCADE,

        CONSTRAINT CK_CW2_USER_STATISTICS_TotalHikes
            CHECK (TotalHikes >= 0),

        CONSTRAINT CK_CW2_USER_STATISTICS_TotalDistance
            CHECK (TotalDistance >= 0),

        CONSTRAINT CK_CW2_USER_STATISTICS_TotalDuration
            CHECK (TotalDuration >= 0)
    );
END;
GO

SELECT
    UserID,
    TotalHikes,
    TotalDistance,
    TotalDuration
FROM CW2.USER_STATISTICS;
GO