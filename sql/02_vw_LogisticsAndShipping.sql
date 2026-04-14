CREATE OR ALTER VIEW dbo.vw_LogisticsAndShipping AS
SELECT
    O.OrderID,
    O.CustomerID,
    O.ShippedDate,
    O.RequiredDate,
    O.Freight,
    O.ShipCountry,
    S.CompanyName AS ShipperName,
    E.FirstName + ' ' + E.LastName AS EmployeeName,
    DATEDIFF(DAY, O.OrderDate, O.ShippedDate) AS DeliveryDuration,
    CASE WHEN O.ShippedDate > O.RequiredDate THEN 1 ELSE 0 END AS IsLate
FROM Orders O
LEFT JOIN Shippers S ON O.ShipVia = S.ShipperID
LEFT JOIN Employees E ON O.EmployeeID = E.EmployeeID;
