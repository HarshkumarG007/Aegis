import ipaddress
import socket
import ssl
from urllib.parse import urlparse
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util import connection

class SSRFViolation(Exception):
    pass

def is_safe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        # Reject private, loopback, link-local, multicast, unspecified
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return False
        
        # Explicitly block cloud metadata (169.254.0.0/16)
        # is_link_local already catches 169.254.0.0/16, but we check explicitly just in case.
        if isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.IPv4Network("169.254.0.0/16"):
            return False
            
        # Block IPv4-mapped IPv6
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            return is_safe_ip(str(ip.ipv4_mapped))
            
        return True
    except ValueError:
        return False

def resolve_and_validate(hostname: str) -> str:
    """
    Resolve the hostname to an IP and validate it.
    Returns the first safe IP. Raises SSRFViolation if any resolved IP is unsafe,
    or if resolution fails.
    """
    try:
        # Get all addresses (IPv4 and IPv6)
        addrinfo = socket.getaddrinfo(hostname, None, 0, socket.SOCK_STREAM)
    except socket.gaierror:
        raise SSRFViolation(f"DNS resolution failed for {hostname}")
        
    safe_ips = []
    for family, _, _, _, sockaddr in addrinfo:
        ip_str = sockaddr[0]
        if not is_safe_ip(ip_str):
            raise SSRFViolation(f"DNS resolution returned forbidden IP: {ip_str}")
        safe_ips.append(ip_str)
        
    if not safe_ips:
        raise SSRFViolation(f"No valid IP addresses resolved for {hostname}")
        
    # Return the first safe IP to pin
    return safe_ips[0]

class PinnedHTTPConnection(urllib3.connection.HTTPSConnection):
    def __init__(self, *args, pinned_ip=None, original_host=None, **kwargs):
        self.pinned_ip = pinned_ip
        self.original_host = original_host
        super().__init__(*args, **kwargs)

    def connect(self):
        # Override the connection logic to connect to the pinned IP
        # but retain the original host for TLS SNI and certificate verification.
        
        # Connect to the pinned IP
        self.sock = connection.create_connection(
            (self.pinned_ip, self.port),
            self.timeout,
            self.source_address,
            self.socket_options,
        )
        
        # Wrap the socket with SSL, providing the original hostname for SNI
        context = ssl.create_default_context()
        self.sock = context.wrap_socket(self.sock, server_hostname=self.original_host)
        
        # The certificate is automatically verified against self.original_host by default context.
        # No verify=False escape hatches!
        
class PinnedHTTPSConnectionPool(urllib3.HTTPSConnectionPool):
    ConnectionCls = PinnedHTTPConnection

    def __init__(self, host, port=None, pinned_ip=None, **kwargs):
        self.pinned_ip = pinned_ip
        super().__init__(host, port, **kwargs)

    def _new_conn(self):
        self.num_connections += 1
        return self.ConnectionCls(
            host=self.host,
            port=self.port,
            timeout=self.timeout.connect_timeout,
            pinned_ip=self.pinned_ip,
            original_host=self.host,
            **self.conn_kw,
        )

def safe_fetch(url: str, max_redirects: int = 5, timeout: float = 5.0, max_size: int = 1048576) -> bytes:
    """
    Safely fetch a URL protecting against SSRF, DNS rebinding, infinite redirects, and large bodies.
    """
    current_url = url
    redirects_followed = 0
    
    while redirects_followed <= max_redirects:
        parsed = urlparse(current_url)
        
        if parsed.scheme != "https":
            raise SSRFViolation("Only HTTPS is allowed.")
            
        hostname = parsed.hostname
        if not hostname:
            raise SSRFViolation("Invalid URL.")
            
        # 1. Resolve and Validate
        pinned_ip = resolve_and_validate(hostname)
        port = parsed.port or 443
        
        # 2. Pin the Connection
        pool = PinnedHTTPSConnectionPool(
            host=hostname, 
            port=port, 
            pinned_ip=pinned_ip,
            cert_reqs='CERT_REQUIRED' # Enforce TLS cert verification
        )
        
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
            
        # 3. Execute request with strict timeout
        # Using preload_content=False to allow checking response size before downloading everything
        response = pool.request(
            'GET', 
            path, 
            retries=False, 
            timeout=urllib3.Timeout(connect=timeout, read=timeout),
            preload_content=False,
            redirect=False
        )
        
        # 4. Handle Redirects Manually
        if response.status in (301, 302, 303, 307, 308):
            redirects_followed += 1
            redirect_url = response.headers.get('Location')
            if not redirect_url:
                raise SSRFViolation("Redirect missing Location header.")
            
            from urllib.parse import urljoin
            current_url = urljoin(current_url, redirect_url)
            continue
            
        # 5. Read response with size limits (Resource Limits)
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > max_size:
            raise ValueError("Response exceeds max size limit.")
            
        body = b""
        for chunk in response.stream(8192):
            body += chunk
            if len(body) > max_size:
                raise ValueError("Response exceeds max size limit during streaming.")
                
        return body
        
    raise SSRFViolation("Maximum redirects exceeded.")
