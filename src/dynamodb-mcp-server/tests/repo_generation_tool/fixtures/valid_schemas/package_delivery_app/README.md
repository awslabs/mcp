# Multi-Attribute Keys Example (Package Delivery Platform)

This example demonstrates DynamoDB's **multi-attribute GSI keys** feature using a package delivery platform data model. GSI partition and sort keys composed of multiple separate attributes (up to 4 each), eliminating synthetic key concatenation in GSIs.

## Architecture Overview

Multi-table design with multi-attribute GSI sort keys throughout. This is the only fixture that tests multi-attribute keys — no other fixture schema uses array format for `partition_key`, `sort_key`, `pk_template`, or `sk_template`.

## Key Scenarios Covered

- **Multi-attribute SK with numeric type**: `WarehousesByCity` SK `["category", "rating"]` where `rating` is decimal
- **Multi-attribute SK with composite value**: `ProductsByCategory` SK `["category", "sort_key"]` where `sort_key` contains `MENU#...` prefixed values
- **Multi-attribute SK with INCLUDE projection**: `ShipmentsByRecipient`, `ShipmentsByWarehouse`, `ShipmentsByCourier`, `WarehousesByCity`, `ProductsByCategory`
- **Multi-attribute SK with KEYS_ONLY projection**: `WarehousesByName` (single-attribute SK for comparison)
- **Multi-attribute SK with range condition**: `WarehousesByCity` with `>=` on `rating`
- **Sparse GSI with single-attribute key**: `CourierActiveDelivery` (PK only, no SK)
- **Mixed GSI designs on same table**: Shipments table has 5 GSIs mixing multi-attribute SK, single-attribute SK, and PK-only
- **Polymorphic item collection**: Warehouses table with WarehouseProfile, Product, Rating sharing base table
- **Partition-key-only tables**: Recipients, Couriers (no SK, no GSI multi-attribute keys)
- **Multiple entities sharing a GSI**: Product and WarehouseProfile both map to `WarehousesByCity`/`WarehousesByName`

## Tables and Entities

### Recipients Table (PK only, no GSI)
- **Recipient**: Simple key-value lookup

### Couriers Table (PK only, no GSI)
- **Courier**: Simple key-value lookup

### Warehouses Table (Item Collection)
- **WarehouseProfile**: `SK = "PROFILE"`, maps to `WarehousesByCity` (multi-attr SK) and `WarehousesByName` (single SK)
- **Product**: `SK = "MENU#{category}#{product_id}"`, maps to `ProductsByCategory` (multi-attr SK with composite value)
- **Rating**: `SK = "REVIEW#{created_at}#{rating_id}"`, no GSI mapping

### Shipments Table (5 GSIs)
- **Shipment**: Maps to `ShipmentsByRecipient`, `ShipmentsByWarehouse`, `ShipmentsByCourier` (all multi-attr SK `["status", "created_at"]`), `AvailableShipmentsByCity` (single SK), `CourierActiveDelivery` (PK only, sparse)

## Multi-Attribute Key Patterns

| GSI | PK | SK | Projection | Notable |
|-----|----|----|------------|---------|
| WarehousesByCity | `city` | `["category", "rating"]` | INCLUDE | Decimal SK, range `>=` on rating |
| WarehousesByName | `city` | `name` | KEYS_ONLY | Single-attribute for comparison |
| ProductsByCategory | `city` | `["category", "sort_key"]` | INCLUDE | Composite value in multi-attr SK |
| ShipmentsByRecipient | `recipient_id` | `["status", "created_at"]` | INCLUDE | Equality on status, range on date |
| ShipmentsByWarehouse | `warehouse_id` | `["status", "created_at"]` | INCLUDE | Same pattern, different PK |
| ShipmentsByCourier | `courier_id` | `["status", "created_at"]` | INCLUDE | Same pattern, different PK |
| AvailableShipmentsByCity | `available_city` | `created_at` | INCLUDE | Single SK, sparse |
| CourierActiveDelivery | `active_delivery` | — | INCLUDE | PK only, sparse |
