CREATE OR ALTER VIEW dbo.vw_CustomerAnalytics AS
SELECT
    C.CustomerID,
    C.CompanyName,
    C.Country,
    C.City
FROM Customers C;
