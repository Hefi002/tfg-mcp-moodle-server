# Installation and Configuration

## Installation

See full details in the architecture section and README.

```bash
# Clone repository
git clone https://github.com/yourusername/tfg-mcp-moodle-server.git
cd tfg-mcp-moodle-server

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Configuration

### 1. Create .env file

Copy the example file and configure it:

```bash
cp .env.example .env
```

### 2. Configure environment variables

Edit the `.env` file:

```env
# Moodle Configuration
MOODLE_URL=http://localhost:8000
MOODLE_TOKEN=your_webservice_token_here
```

### 3. Get Moodle Token

In your Moodle instance:

1. Go to **Site administration > Plugins > Web services > Manage tokens**
2. Create a new token or use an existing one
3. Copy the token and paste it in `.env`

## Configuration with Claude Desktop

### 1. Locate configuration file

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 2. Add MCP server

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "moodle": {
      "command": "python",
      "args": [
        "-m",
        "src.mcp.server"
      ],
      "cwd": "C:\\full\\path\\to\\tfg-mcp-moodle-server",
      "env": {
        "MOODLE_URL": "http://localhost:8000",
        "MOODLE_TOKEN": "your_token_here"
      }
    }
  }
}
```

**Note**: Adjust the `cwd` path to the actual location of your project.

### 3. Restart Claude Desktop

Completely close Claude Desktop and open it again.

### 4. Verify connection

In Claude, you should see the Moodle tools available in the connectors section.

## Usage Examples

### Example 1: List Courses

Ask Claude:

```
Can you show me all available courses in Moodle?
```

Claude will use the `get_courses` tool automatically.

### Example 2: Create a Course

```
Create a course called "Introduction to Python 2024" 
with short code "PY101" in category 1
```

Claude will use `create_courses` with the appropriate parameters.

### Example 3: Enroll User

```
Enroll user with ID 5 in course with ID 10 
with the student role (roleid 5)
```

Claude will use `manual_enrol_users`.

## Advanced Configuration

### Additional Environment Variables

```env
# Optional: Logging configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Optional: HTTP request timeout
HTTP_TIMEOUT=30
```

### Development Configuration

For development, create a `.env.development`:

```env
MOODLE_URL=http://localhost:8000
MOODLE_TOKEN=development_token
LOG_LEVEL=DEBUG
```

And use it:

```bash
# Linux/Mac
export $(cat .env.development | xargs)

# Windows PowerShell
Get-Content .env.development | ForEach-Object { 
    if($_ -match "^([^=]+)=(.*)$") { 
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process") 
    } 
}
```

## Troubleshooting

### Server doesn't connect

1. Verify that environment variables are correctly configured
2. Verify that the Moodle token is valid
3. Verify that Moodle has Web Services enabled
4. Check server logs

### Claude doesn't recognize the tools

1. Verify that `claude_desktop_config.json` is correctly formatted
2. Completely restart Claude Desktop
3. Verify that the `cwd` path is correct
4. Verify that Python is in the PATH

### Moodle permission errors

If you receive permission errors:

1. Verify that the token user has the necessary capabilities
2. Check Moodle logs for more details
3. Make sure the user has permissions in the correct context

## Next Steps

- [Architecture](architecture.md) - Understand how the system works
- [API Reference](api.md) - Complete API documentation
- [Testing](testing.md) - Run and write tests
