# MCP Documentation and Knowledge Tools

Part of [Aurora DSQL MCP Tools Reference](../mcp-tools.md).

---

## 4. dsql_search_documentation - Search Aurora DSQL documentation

**Use for:** Finding relevant documentation, looking up features, troubleshooting

**Parameters:**

- `search_phrase` (string, required) - Search query
- `limit` (int, optional) - Maximum number of results

**Returns:** Dictionary of search results with URLs and snippets

**Example:**

```python
search_phrase = "foreign key constraints"
limit = 5
```

---

## 5. dsql_read_documentation - Read specific DSQL documentation pages

**Use for:** Retrieving detailed documentation content

**Parameters:**

- `url` (string, required) - URL of documentation page
- `start_index` (int, optional) - Starting character index
- `max_length` (int, optional) - Maximum characters to return

**Returns:** Dictionary with documentation content

**Example:**

```python
url = "https://docs.aws.amazon.com/aurora-dsql/latest/userguide/..."
start_index = 0
max_length = 5000
```

---

## 6. dsql_recommend - Get DSQL best practice recommendations

**Use for:** Getting contextual recommendations for DSQL usage

**Parameters:**

- `url` (string, required) - URL of documentation page to get recommendations for

**Returns:** Dictionary with recommendations
