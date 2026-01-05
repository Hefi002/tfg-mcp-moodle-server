# Installation and Usage

## Installation

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/tfg-mcp-moodle-server.git
   cd tfg-mcp-moodle-server
   ```

2. **Create a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the interactive setup:**
   ```bash
   python setup.py
   ```

   The setup script will guide you through configuring your Moodle URL, authentication token, and logging preferences. It will automatically create and configure the `.env` file for you.

5. **Verify the installation:**
   ```bash
   pytest
   ```

### Manual Setup

If you prefer to configure manually:

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your configuration:**
   ```env
   MOODLE_URL=https://your-moodle-instance.com
   MOODLE_TOKEN=your_authentication_token_here
   LOG_LEVEL=INFO
   DEBUG=false
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Getting Your Moodle Token

### For Administrators: Creating Tokens

1. **Navigate to token management:**
   - Log in to Moodle as administrator
   - Go to: `Site administration` → `Server` → `Web services` → `Manage tokens`

2. **Create a new token:**
   - Select the user for whom you're creating the token
   - Choose the web service (Something like `MCP API service`, ask your Moodle admin in case of doubt)
   - Optionally set expiration date and IP restrictions
   - Click "Save changes"
   - Copy the generated token immediately

3. **Configure permissions:**
   - Tokens inherit permissions from the user's role
   - Default roles include: Administrator, Manager, Teacher, Student, etc.
   - For fine-grained control, create custom roles with specific capabilities

### For Teachers and Students: Obtaining a Token

1. **Check if self-service tokens are enabled:**
   - Log in to your Moodle account
   - Go to: `Preferences` → `Security` → `Security keys`
   - If available, you can generate your own token here
   - If an existing token is shown for this webservice but you don't know it, choose Reset to generate a new one

2. **If self-service is not available:**
   - Contact your Moodle site administrator
   - Request a token with appropriate permissions for your use case
   - The administrator can create the token following the steps above

### Advanced: Custom Roles and Permissions

For organizations requiring specific permission sets, Moodle offers granular permission control at system, category, course, and activity levels. You can create custom roles tailored to your needs:

1. Go to: `Site administration` → `Users` → `Permissions` → `Define roles`
2. Add a new role or duplicate an existing one
3. Configure specific capabilities for the role
4. Ensure the role has `webservice/rest:use` capability for API access

**Additional Resources:**
- [Moodle Roles and Permissions Documentation](https://docs.moodle.org/501/en/Roles_and_permissions)
- [Web Services Documentation](https://docs.moodle.org/501/en/Web_services)
- [Web Services Security](https://docs.moodle.org/501/en/Web_services_security)

## Configuration

### Environment Variables

The server uses the following environment variables (configured in `.env`):

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MOODLE_URL` | Your Moodle instance URL | - | Yes |
| `MOODLE_TOKEN` | Authentication token from Moodle | - | Yes |
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) | INFO | No |
| `DEBUG` | Enable debug mode (true/false) | false | No |

### Security Best Practices

- Never commit your `.env` file to version control
- Keep your tokens secure and rotate them regularly
- Use HTTPS for production Moodle instances
- Apply IP restrictions when possible for tokens
- Set expiration dates for tokens in production

## Configuration with Claude Desktop

Claude Desktop is used as example, each AI has its methods of adding an MCP tool.

### 1. Locate configuration file

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 2. Add MCP server

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcpMoodleAPI": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "C:\\full\\path\\to\\tfg-mcp-moodle-server",
      "env": {
        "PYTHONPATH": "C:\\full\\path\\to\\tfg-mcp-moodle-server"
      }
    }
  }
}
```

**Note**: Adjust the `cwd` and `PYTHONPATH` to the actual location of your project.

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
