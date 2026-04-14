CREATE OR ALTER VIEW dbo.vw_MasterSales AS
SELECT
    O.OrderID,
    O.CustomerID,
    O.OrderDate,
    P.ProductID,
    P.ProductName,
    C.CategoryName,
    P.UnitCost,
    OD.UnitPrice,
    OD.Quantity,
    OD.Discount,
    (OD.UnitPrice * OD.Quantity) AS GrossSales,
    (OD.UnitPrice * OD.Quantity * (1 - OD.Discount)) AS NetSales,
    ((OD.UnitPrice * OD.Quantity * (1 - OD.Discount)) - (OD.Quantity * P.UnitCost)) AS Profit
FROM Orders O
JOIN [Order Details] OD ON O.OrderID = OD.OrderID
JOIN Products P ON OD.ProductID = P.ProductID
JOIN Categories C ON P.CategoryID = C.CategoryID;
