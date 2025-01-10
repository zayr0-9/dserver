# import socket

# def get_local_ip():
#     try:
#         # Connect to an external server to determine the local network IP
#         with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
#             # Using a public IP address, no data is sent out
#             s.connect(("8.8.8.8", 80))
#             ip_address = s.getsockname()[0]
#         return ip_address
#     except Exception as e:
#         print(f"Error getting local IP: {e}")
#         return "127.0.0.1"  # Fallback to localhost

# # Example usage
# local_ip = get_local_ip()
# print(f"Local IP: {local_ip}")


import socket

def get_local_ip():
    try:
        # Create a dummy socket and connect to a non-routable address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Use a non-routable address to identify the active interface
            s.connect(("192.168.0.1", 1))  # Common LAN address, no actual connection needed
            ip_address = s.getsockname()[0]
        return ip_address
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return "127.0.0.1"  # Fallback to localhost

# Example usage
local_ip = get_local_ip()
print(f"Local IP: {local_ip}")
