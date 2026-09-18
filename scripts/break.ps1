# NETRA Break Script — Windows PowerShell runner
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Resolve-Path "$ScriptDir\..\backend"
$env:PYTHONPATH = "$BackendDir;$env:PYTHONPATH"
python "$ScriptDir\break.py" @args
