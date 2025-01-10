import subprocess
import os
import sys
import threading
import signal


def read_output(name, pipe):
    # Use a loop to read from the pipe
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
    processes = []
    nginx_process = None  # Keep track of nginx separately

    try:
        # Use the current working directory as the script directory
        script_dir = os.getcwd()

        # set conf

        # Define the relative path to the target script
        print("loading nginx conf")
        script_path = os.path.join("nginx-rtmp-win32-1.2.1", "driveLoad.py")

        # Execute the target script
        try:
            subprocess.run(["python", script_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error occurred while running the script: {e}")

        # Start nginx
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
        # Not adding nginx_process to processes list since we'll stop it differently

         # Start waitress-serve
        print("Starting waitress-serve...")
        waitress_command = [
            os.path.join(script_dir, 'myvenv', 'Scripts', 'python.exe'),
            '-m', 'waitress', '--port=8000', 'filetransfer.wsgi:application'
        ]
        waitress_process = subprocess.Popen(
            waitress_command,
            cwd=os.path.join(script_dir, 'filetransfer'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE  # Changed to stderr for error output
        )
        processes.append(('waitress', waitress_process))
        
        print("\nServers are running.")
        print("Press any key to stop the servers.")

        # Start threads to read outputs
        threads = []
        for name, proc in processes:
            t = threading.Thread(target=read_output, args=(name, proc.stdout))
            t.daemon = True  # Allows threads to exit when main program exits
            t.start()
            threads.append(t)

        # Wait for user input to stop the servers
        while True:
            try:
                if any(proc.poll() is not None for _, proc in processes):
                    # If any process has terminated, exit the loop
                    print("\nOne of the servers has stopped unexpectedly.")
                    break
                # Check for user input
                if sys.platform == 'win32':
                    import msvcrt
                    if msvcrt.kbhit():
                        msvcrt.getch()  # Consume the key press
                        print("\nStopping servers...")
                        break
                else:
                    # For Unix-like systems
                    import select
                    if select.select([sys.stdin], [], [], 1)[0]:
                        sys.stdin.readline()
                        print("\nStopping servers...")
                        break
            except KeyboardInterrupt:
                print("\nStopping servers...")
                break

        # Terminate all processes
        for name, proc in processes:
            if proc.poll() is None:
                print(f"Stopping {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

        # Stop nginx
        if nginx_process and nginx_process.poll() is None:
            print("Stopping nginx...")
            nginx_stop_command = [nginx_exe, '-s', 'stop']
            subprocess.run(nginx_stop_command, cwd=nginx_dir)
            nginx_process.wait(timeout=5)

        # Wait for threads to finish
        for t in threads:
            t.join()

        print("Servers stopped.")
        sys.exit(0)

    except Exception as e:
        print(f"An error occurred: {e}")
        # Terminate all processes in case of an error
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
        # Stop nginx
        if nginx_process and nginx_process.poll() is None:
            print("Stopping nginx due to error...")
            nginx_stop_command = [nginx_exe, '-s', 'stop']
            subprocess.run(nginx_stop_command, cwd=nginx_dir)
        sys.exit(1)


if __name__ == "__main__":
    main()
