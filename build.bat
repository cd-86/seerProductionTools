pyinstaller -y -w -n productionTools .\main.py
ROBOCOPY RBKVersion dist/productionTools/RBKVersion /MIR
