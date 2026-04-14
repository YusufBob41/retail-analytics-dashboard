CREATE OR ALTER VIEW dbo.vw_InventoryPerformance AS
SELECT
    P.ProductID,
    P.ProductName,
    P.UnitsInStock,
    P.ReorderLevel,
    P.Discontinued,
    C.CategoryName,
    S.CompanyName AS SupplierName,
    (P.UnitsInStock * P.UnitCost) AS StockValue
FROM Products P
JOIN Categories C ON P.CategoryID = C.CategoryID
JOIN Suppliers S ON P.SupplierID = S.SupplierID;
