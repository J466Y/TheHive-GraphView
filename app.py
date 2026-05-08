#!/usr/bin/env python3
import argparse
import sys
import os
import subprocess

def run_collector():
    print("Iniciando el colector de métricas...")
    cmd = [sys.executable, "src/collector.py"]
    subprocess.run(cmd)

def run_setup():
    print("Iniciando la configuración de Grafana...")
    cmd = [sys.executable, "src/setup_grafana.py"]
    subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="Launcher para TheHive GraphView Dashboard")
    parser.add_argument("command", choices=["run", "setup"], help="Comando a ejecutar: 'run' para el colector, 'setup' para la configuración de Grafana")
    
    args = parser.parse_args()
    
    # Asegurarse de que estamos en el directorio raíz del proyecto
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if args.command == "run":
        run_collector()
    elif args.command == "setup":
        run_setup()

if __name__ == "__main__":
    main()
