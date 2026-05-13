import sys
print("Python works", flush=True)
print(f"Python version: {sys.version}", flush=True)

print("Importing ortools...", flush=True)
from ortools.sat.python import cp_model
print("ortools OK", flush=True)

print("Importing engine...", flush=True)
from app.core.scheduler.engine import ShiftScheduler, EmployeeData, ShiftSlot
print("engine OK", flush=True)
print("הכל תקין!", flush=True)
