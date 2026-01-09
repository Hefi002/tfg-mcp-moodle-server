# Installation and Usage

## Installation

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Hefi002/tfg-mcp-moodle-server.git
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

4. **Install development dependencies (for testing):**
   ```bash
   pip install -r requirements-dev.txt
   ```

5. **Run the interactive setup:**
   ```bash
   python setup.py
   ```

   The setup script will guide you through configuring your Moodle URL, authentication token, and logging preferences. It will automatically create and configure the `.env` file for you.

6. **Verify the installation:**
   ```bash
   pytest
   ```

   > **Note:** You need to install `requirements-dev.txt` to run pytest (step 4).

### Manual Setup

If you prefer to configure your .env manually (step 5 on installation):

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

## Usage

### Starting the Server

1. **Activate your virtual environment:**
   ```bash
   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```
   
2. **Run the server:**
   ```bash
   python -m src
   ```
   
   Or alternatively:
   ```bash
   python -m src.mcp.server
   ```

3. **To close the server once you are done:**
    - Press `CTRL + C` in the terminal
    - Then exit your virtual environment:
    ```bash
    deactivate
    ```

### Connecting with Claude Desktop

Claude Desktop is used as example, each AI has its methods of adding an MCP tool.

To add the server to your Claude Desktop configuration:

1. Open Claude Desktop and go to `Settings`.
2. Navigate to the `Developer` section, then choose `Edit config`.
3. Edit the file `claude_desktop_config.json` to add the following MCP server configuration:

#### Windows

```json
{
  "mcpServers": {
    "moodle-api": {
      "command": "C:\\path\\to\\tfg-mcp-moodle-server\\venv\\Scripts\\python.exe",
      "args": ["-m", "src.mcp.server"],
      "cwd": "C:\\path\\to\\tfg-mcp-moodle-server",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\tfg-mcp-moodle-server"
      }
    }
  }
}
```

**Important notes:**
- Replace `C:\\path\\to\\tfg-mcp-moodle-server` with the actual path where you cloned the project
- The "command" path must point to the `python.exe` inside your `venv` folder

#### Linux/macOS

```json
{
  "mcpServers": {
    "moodle-api": {
      "command": "/path/to/tfg-mcp-moodle-server/venv/bin/python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/tfg-mcp-moodle-server",
      "env": {
        "PYTHONPATH": "/path/to/tfg-mcp-moodle-server"
      }
    }
  }
}
```

**Important notes:**
- Replace `/path/to/tfg-mcp-moodle-server` with the actual path where you cloned the project
- Use forward slashes (`/`) in paths for Linux/macOS
- The path must point to the `python` executable inside your `venv` folder

4. Once added, restart Claude Desktop to apply the changes.

### Example Usage

Once connected, you can use natural language to interact with Moodle:

```
"Show me all courses in my Moodle instance"
"Get the enrolled users in course ID 5"
"What's the completion status for user 10 in course 3?"
"List all assignments in course 'Introduction to Python'"
```

## Troubleshooting

### Error: "Could not attach to MCP server"

Verify the following:

1. **Correct path to Python in venv:**
   ```bash
   # Windows - verify this file exists:
   C:\path\to\tfg-mcp-moodle-server\venv\Scripts\python.exe
   
   # Linux/macOS - verify this file exists:
   /path/to/tfg-mcp-moodle-server/venv/bin/python
   ```

2. **Dependencies installed:**
   ```bash
   # Activate venv and verify they are installed
   # Windows
   venv\Scripts\activate
   pip list
   
   # Linux/macOS
   source venv/bin/activate
   pip list
   ```

3. **`.env` file configured:**
   ```bash
   # Verify it exists in the project root
   ls .env  # or dir .env on Windows
   ```

4. **Correct JSON syntax:**
   - On Windows: use `\\` in paths
   - On Linux/macOS: use `/` in paths
   - Don't forget commas between elements

### Claude doesn't recognize the tools

1. Verify that `claude_desktop_config.json` is correctly formatted
2. **Completely** restart Claude Desktop (close it from the system tray if it's there)
3. Verify that the `cwd` path is correct
4. Check Claude Desktop logs for more details

**Log locations:**
- **Windows:** `%APPDATA%\Claude\logs\`
- **macOS:** `~/Library/Logs/Claude/`
- **Linux:** `~/.config/Claude/logs/`

### Moodle permission errors

If you receive permission errors:

1. Verify that the token user has the necessary capabilities
2. Check Moodle logs for more details
3. Make sure the user has permissions in the correct context (system, category, or course)
4. Verify that Web Services are enabled in your Moodle instance

## Other Documentation

- [Architecture](architecture.md) - Understand how the system works
- [API Reference](api.md) - Complete API documentation
- [Testing](testing.md) - Run and write tests
