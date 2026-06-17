# Line Protocol

InfluxDB, v2 and v3, uses line protocol to write data points. It is a text-based format that provides the measurement, tag set, field set, and timestamp of a data point.

## Line Protocol Format

```
measurement,tag1=val1,tag2=val2 field1=1.0,field2="hello" timestamp
```

Rules:
- **Tags** — indexed key-value strings, used for filtering. Optional but recommended.
- **Fields** — non-indexed data values. At least one required per point.
- **Timestamp** — Unix epoch. Omit to use server time (not recommended for production).
- Sort tags alphabetically for best write compression.
- No spaces in tag keys, tag values, or field keys. Escape commas and spaces in values with `\`.

Escaping rules:
| Location | Characters to escape |
|----------|---------------------|
| Measurement name | `,` and ` ` (space) |
| Tag keys & values | `,`, `=`, and ` ` (space) |
| Field keys | `,`, `=`, and ` ` (space) |
| Field string values | `"` (double-quote) — wrap value in `"` and escape internal quotes as `\"` |

Example with escaping: `cpu,host=web\ server01,region=us\,east usage_idle=98.2`

Field value types:
| Type | Syntax | Example |
|------|--------|---------|
| Float | bare number | `temp=72.3` |
| Integer | trailing `i` | `count=10i` |
| String | double-quoted | `status="ok"` |
| Boolean | `true`/`false` | `active=true` |

Type is inferred on first write and locked — writing a different type to the same field causes an error and the conflicting point is dropped.

