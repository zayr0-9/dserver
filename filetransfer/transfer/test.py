import subprocess


def terminal():
    result = subprocess.run("dir", shell=True, capture_output=True, text=True)
    print("Output: ", result.stdout)
    print("Errors (if any): ", result.stderr)


terminal()
