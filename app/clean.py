import shutil
import os


for parent, dirnames, filenames in os.walk('./'):
    for dn in dirnames:
        print(f"{parent}/{dn}")

        if dn == '__pycache__':
            shutil.rmtree(f"{parent}/{dn}")
        if dn == 'migrations':
            for file in os.listdir(f"{parent}/{dn}"):
                if file != "__init__.py" and file != "__pycache__":
                    os.remove(f"{parent}/{dn}/{file}")
