# Routing

This guide explains how routing works in milkcrate and how to handle routes correctly in your deployed applications.

## How Routing Works

Milkcrate uses **Traefik** as a reverse proxy with **PathPrefix** routing and **prefix stripping**:

1. **User Request**: `http://localhost/my-app/api/users`
2. **Traefik Matching**: Matches `PathPrefix(/my-app)`
3. **Prefix Stripping**: Removes `/my-app` from the path
4. **Container Receives**: `GET /api/users`

Your containerized app should define routes at the **root level** (`/`, `/api/users`, etc.) - **milkcrate handles the prefix routing automatically.**

## Priority System

Milkcrate calculates router priorities dynamically to prevent conflicts:

```python
priority = 100 + (path_segments * 10) + route_length
```

Examples:

- `/app` → priority 104
- `/app/v1` → priority 115
- `/app/v1/api` → priority 131

Longer, more specific routes get matched first.

## Designing Your App Routes

### Correct: Root-Level Routes

```python
@app.route("/")
def index():
    return "Home"

@app.route("/api/users")
def users():
    return jsonify({"users": [...]})
```

**Result**: Request to `http://localhost/my-app/api/users` → Container receives `GET /api/users`

### Incorrect: Including the Prefix

```python
# DON'T do this - the prefix is already stripped by Traefik
@app.route("/my-app/api/users")
def users():
    return jsonify({"users": [...]})
```

## JavaScript API Calls

When making API calls from JavaScript, use **relative paths** instead of absolute paths.

### The Problem

```javascript
// ❌ WRONG - Won't work when deployed at /my-app
fetch('/api/data')  // Browser requests: http://localhost/api/data
```

When your page is at `http://localhost/my-app/`, an absolute path like `/api/data` goes to the root, not your app.

### Solution: Use Relative Paths

```javascript
// ✅ CORRECT - Works at any deployment route
fetch('api/data')  // Relative path resolves correctly
```

### Solution with Base Tag

Add to your HTML `<head>`:

```html
<base href="{{ request.path.rstrip('/') }}/">
```

Then use simple relative paths everywhere.

### Complete Example

```html
<!DOCTYPE html>
<html>
<head>
    <base href="{{ request.path.rstrip('/') }}/">
</head>
<body>
    <button onclick="loadData()">Load Data</button>
    <div id="result"></div>

    <script>
        async function loadData() {
            try {
                const response = await fetch('api/data');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                document.getElementById('result').textContent = JSON.stringify(data);
            } catch (error) {
                console.error('Error:', error);
            }
        }
    </script>
</body>
</html>
```

## Troubleshooting

### "Unexpected token '<'" Error

**Cause**: API endpoint returning HTML instead of JSON (wrong route).

**Fix**: Use relative paths (`api/data` not `/api/data`).

### Debugging

```bash
# Test route directly
curl http://localhost/my-app/api/data

# Check Traefik configuration
# Visit http://localhost:8080
```

## Reserved Routes

These routes cannot be used for deployed applications:

- `/traefik`, `/admin`, `/login`, `/logout`, `/upload`, `/volumes`, `/settings`

## Summary

- **Use relative paths** in JavaScript: `fetch('api/data')` not `fetch('/api/data')`
- **Define routes at root level**: `/api/users` not `/my-app/api/users`
- **Test locally first**: Verify your app works before deploying
- **Check Traefik dashboard**: Debug routing issues at `http://localhost:8080`

## Next steps

- [CLI Reference](../reference/cli.md)
