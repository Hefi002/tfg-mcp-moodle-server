#Script to stop Moodle Docker containers (Windows)

@echo off
echo Deteniendo Moodle Docker...

set MOODLE_DOCKER_WWWROOT=%~dp0dev-environment\moodle
set MOODLE_DOCKER_DB=pgsql

cd /d %~dp0dev-environment\moodle-docker
call bin\moodle-docker-compose stop

pause