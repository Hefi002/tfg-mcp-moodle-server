#Script to start Moodle Docker containers (Linux)

$env:MOODLE_DOCKER_WWWROOT = "$PSScriptRoot\dev-environment\moodle"
$env:MOODLE_DOCKER_DB = "pgsql"

Set-Location "$PSScriptRoot\dev-environment\moodle-docker"
.\bin\moodle-docker-compose start