import subprocess
import os
import sys
import threading
import signal
import platform


def create_virtualenv():
    venv_path = os.path.join(os.getcwd(), 'myvenv')

    # Check if virtual environment already exists
    if not os.path.exists(venv_path):
        print("Creating virtual environment...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", venv_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")
            sys.exit(1)

    # Determine correct pip path based on OS
    if platform.system() == "Windows":
        pip_path = os.path.join(venv_path, 'Scripts', 'pip.exe')
    else:
        pip_path = os.path.join(venv_path, 'bin', 'pip')

    # Install requirements
    print("Installing requirements...")
    try:
        subprocess.run([pip_path, "install", "-r",
                       "requirements.txt"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        sys.exit(1)


def read_output(name, pipe):
    while True:
        line = pipe.readline()
        if line:
            try:
                decoded_line = line.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                decoded_line = line.decode('utf-8', errors='ignore')
            print(f"[{name}] {decoded_line.strip()}")
        else:
            break


def main():
    # Set up virtual environment first
    create_virtualenv()

    processes = []
    nginx_process = None

    try:
        script_dir = os.getcwd()

        print("loading nginx conf")
        script_path = os.path.join("nginx-rtmp-win32-1.2.1", "driveLoad.py")

        try:
            subprocess.run(["python", script_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running the script: {e}")

        print("Starting Nginx...")
        nginx_dir = os.path.join(script_dir, 'nginx-rtmp-win32-1.2.1')
        print(f"nginx_dir = {nginx_dir}")
        nginx_exe = os.path.join(nginx_dir, 'nginx.exe')
        print(f"nginx_exe = {nginx_exe}")
        nginx_process = subprocess.Popen(
            [nginx_exe],
            cwd=nginx_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        print("Starting waitress-serve...")
        # Get correct Python path from virtual environment
        if platform.system() == "Windows":
            python_path = os.path.join(
                script_dir, 'myvenv', 'Scripts', 'python.exe')
        else:
            python_path = os.path.join(script_dir, 'myvenv', 'bin', 'python')

        waitress_command = [
            python_path,
            '-m', 'waitress', '--port=8000', 'filetransfer.wsgi:application'
        ]
        waitress_process = subprocess.Popen(
            waitress_command,
            cwd=os.path.join(script_dir, 'filetransfer'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(('waitress', waitress_process))

        print("\nServers are running.")
        print("Press any key to stop the servers.")

        threads = []
        for name, proc in processes:
            t = threading.Thread(target=read_output, args=(name, proc.stdout))
            t.daemon = True
            t.start()
            threads.append(t)

        while True:
            try:
                if any(proc.poll() is not None for _, proc in processes):
                    print("\nOne of the servers has stopped unexpectedly.")
                    break
                if sys.platform == 'win32':
                    import msvcrt
                    if msvcrt.kbhit():
                        msvcrt.getch()
                        print("\nStopping servers...")
                        break
                else:
                    import select
                    if select.select([sys.stdin], [], [], 1)[0]:
                        sys.stdin.readline()
                        print("\nStopping servers...")
                        break
            except KeyboardInterrupt:
                print("\nStopping servers...")
                break

        for name, proc in processes:
            if proc.poll() is None:
                print(f"Stopping {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

        if nginx_process and nginx_process.poll() is None:
            print("Stopping nginx...")
            nginx_stop_command = [nginx_exe, '-s', 'stop']
            subprocess.run(nginx_stop_command, cwd=nginx_dir)
            nginx_process.wait(timeout=5)

        for t in threads:
            t.join()

        print("Servers stopped.")
        sys.exit(0)

    except Exception as e:
        print(f"An error occurred: {e}")
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
        if nginx_process and nginx_process.poll() is None:
            print("Stopping nginx due to error...")
            nginx_stop_command = [nginx_exe, '-s', 'stop']
            subprocess.run(nginx_stop_command, cwd=nginx_dir)
        sys.exit(1)


if __name__ == "__main__":
    main()
