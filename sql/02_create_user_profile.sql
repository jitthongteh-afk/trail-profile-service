USE [Assessment1DB];
GO

IF OBJECT_ID(N'CW2.USER_PROFILE', N'U') IS NULL
BEGIN
    CREATE TABLE CW2.USER_PROFILE
    (
        UserID INT IDENTITY(1,1) NOT NULL,
        Username NVARCHAR(50) NOT NULL,
        FirstName NVARCHAR(50) NULL,
        LastName NVARCHAR(50) NULL,
        Email NVARCHAR(100) NULL,
        Location NVARCHAR(100) NULL,
        ProfilePhoto NVARCHAR(255) NULL,

        RoleID INT NOT NULL
            CONSTRAINT DF_CW2_USER_PROFILE_RoleID
            DEFAULT (1),

        CreatedDate DATE NOT NULL
            CONSTRAINT DF_CW2_USER_PROFILE_CreatedDate
            DEFAULT (CONVERT(DATE, SYSUTCDATETIME())),

        CONSTRAINT PK_CW2_USER_PROFILE
            PRIMARY KEY (UserID),

        CONSTRAINT UQ_CW2_USER_PROFILE_Username
            UNIQUE (Username),

        CONSTRAINT CK_CW2_USER_PROFILE_Username
            CHECK (LEN(LTRIM(RTRIM(Username))) > 0),

        CONSTRAINT CK_CW2_USER_PROFILE_Email
            CHECK (
                Email IS NULL
                OR LEN(LTRIM(RTRIM(Email))) > 0
            ),

        CONSTRAINT FK_CW2_USER_PROFILE_ROLE
            FOREIGN KEY (RoleID)
            REFERENCES CW2.ROLE (RoleID)
    );
END;
GO


IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'CW2.USER_PROFILE')
      AND name = N'UX_CW2_USER_PROFILE_Email'
)
BEGIN
    CREATE UNIQUE INDEX UX_CW2_USER_PROFILE_Email
        ON CW2.USER_PROFILE (Email)
        WHERE Email IS NOT NULL;
END;
GO


SELECT
    UserID,
    Username,
    FirstName,
    LastName,
    Email,
    Location,
    ProfilePhoto,
    RoleID,
    CreatedDate
FROM CW2.USER_PROFILE;
GO