#!/usr/bin/env python
"""
Installation Helper for World Cup Predictor
Handles environment setup and dependency installation.
"""

import subprocess
import sys
import os

def ensure_setuptools():
    """Ensure setuptools is properly installed."""
    try:
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
    except:
        pass
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "setuptools"])
    except:
        pass

def install_dependencies():
    """Install required dependencies with fallback strategies."""
    
    packages = [
        "numpy",
        "pandas",
        "scikit-learn",
        "xgboost",
        "streamlit",
        "matplotlib",
        "plotly",
    ]
    
    print("[*] Installing dependencies...")
    
    for package in packages:
        print(f"[+] Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--prefer-binary", package])
            print(f"[✓] {package} installed")
        except Exception as e:
            print(f"[!] Failed to install {package}: {e}")
            print(f"    Trying with --no-deps...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-deps", package])
            except:
                print(f"[x] Skipping {package}")
    
    print("\n[✓] Installation complete!")

if __name__ == "__main__":
    ensure_setuptools()
    install_dependencies()
