USE [Assessment1DB];
GO


INSERT INTO CW2.USER_PROFILE
(
    Username,
    FirstName,
    LastName,
    Email,
    RoleID
)
SELECT
    source.Username,
    source.FirstName,
    source.LastName,
    source.Email,
    source.RoleID
FROM
(
    VALUES
        (
            N'Grace Hopper',
            N'Grace',
            N'Hopper',
            N'grace@plymouth.ac.uk',
            2
        ),
        (
            N'Tim Berners-Lee',
            N'Tim',
            N'Berners-Lee',
            N'tim@plymouth.ac.uk',
            2
        ),
        (
            N'Ada Lovelace',
            N'Ada',
            N'Lovelace',
            N'ada@plymouth.ac.uk',
            1
        )
) AS source
(
    Username,
    FirstName,
    LastName,
    Email,
    RoleID
)
WHERE NOT EXISTS
(
    SELECT 1
    FROM CW2.USER_PROFILE AS existing
    WHERE existing.Email = source.Email
       OR existing.Username = source.Username
);
GO


SELECT
    p.UserID,
    p.Username,
    p.Email,
    r.RoleName,
    p.CreatedDate
FROM CW2.USER_PROFILE AS p
INNER JOIN CW2.ROLE AS r
    ON p.RoleID = r.RoleID
ORDER BY p.UserID;
GO