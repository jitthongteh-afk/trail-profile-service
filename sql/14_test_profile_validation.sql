USE [Assessment1DB];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

-- Test 1: Reject a blank username.
BEGIN TRY
    BEGIN TRANSACTION;

    EXEC CW2.sp_CreateUserProfile
        @Username = N'   ';

    ROLLBACK TRANSACTION;

    SELECT
        'Blank username' AS TestName,
        'FAIL' AS TestResult,
        'The procedure accepted a blank username.' AS Details;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    SELECT
        'Blank username' AS TestName,
        CASE
            WHEN ERROR_NUMBER() = 50020 THEN 'PASS'
            ELSE 'FAIL'
        END AS TestResult,
        ERROR_NUMBER() AS ActualErrorCode,
        ERROR_MESSAGE() AS Details;
END CATCH;
GO

-- Test 2: Reject a duplicate username.
BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @DuplicateUsername NVARCHAR(50) =
        N'DupTest_' + CONVERT(NVARCHAR(36), NEWID());

    INSERT INTO CW2.USER_PROFILE (Username)
    VALUES (@DuplicateUsername);

    EXEC CW2.sp_CreateUserProfile
        @Username = @DuplicateUsername;

    ROLLBACK TRANSACTION;

    SELECT
        'Duplicate username' AS TestName,
        'FAIL' AS TestResult,
        'The procedure accepted a duplicate username.' AS Details;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    SELECT
        'Duplicate username' AS TestName,
        CASE
            WHEN ERROR_NUMBER() = 50022 THEN 'PASS'
            ELSE 'FAIL'
        END AS TestResult,
        ERROR_NUMBER() AS ActualErrorCode,
        ERROR_MESSAGE() AS Details;
END CATCH;
GO

-- Test 3: Reject an invalid user ID.
BEGIN TRY
    EXEC CW2.sp_ReadUserProfile
        @UserID = -1;

    SELECT
        'Invalid user ID' AS TestName,
        'FAIL' AS TestResult,
        'The procedure accepted an invalid user ID.' AS Details;
END TRY
BEGIN CATCH
    SELECT
        'Invalid user ID' AS TestName,
        CASE
            WHEN ERROR_NUMBER() = 50010 THEN 'PASS'
            ELSE 'FAIL'
        END AS TestResult,
        ERROR_NUMBER() AS ActualErrorCode,
        ERROR_MESSAGE() AS Details;
END CATCH;
GO

-- Confirm that only the original sample profiles remain.
SELECT
    UserID,
    Username,
    Email
FROM CW2.USER_PROFILE
ORDER BY UserID;
GO