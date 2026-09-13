# Sync Github the local repository with the remote repository
    & scripts\git_auto_sync.ps1

# Start the CherryStock chart application
    & python.exe c:/Github/CherryStock/src/webapp/NiceGUI_chart.py


# Render the Archify report Architecture High level
    .\scripts\render_archify_cherrystock.ps1
    # Open High-Level Architecture
    Start-Process ".\docs\architecture\generated\CherryStock_High_Level.html"
    Start-Process ".\docs\architecture\generated\CherryStock_Analytics_Calculation_Engines.html"