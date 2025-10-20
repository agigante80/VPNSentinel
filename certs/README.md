# VPN Sentinel TLS Certificates

This directory contains TLS certificate files for HTTPS encryption.

## Certificate Files

Place the following files in this directory:

- `vpn-sentinel-cert.pem` - TLS certificate file (public key)
- `vpn-sentinel-key.pem` - TLS private key file

## How to Generate Self-Signed Certificates

For testing purposes, you can generate self-signed certificates:

```bash
# Fix OpenSSL RNG issues on some systems (like Synology)
export RANDFILE=/tmp/.rnd
touch /tmp/.rnd

# Generate private key
openssl genrsa -out vpn-sentinel-key.pem 2048

# Generate certificate signing request
RANDFILE=/tmp/.rnd openssl req -new -key vpn-sentinel-key.pem -out vpn-sentinel-cert.csr

# Alternative: If the above fails, try:
# openssl req -new -key vpn-sentinel-key.pem -out vpn-sentinel-cert.csr -rand /dev/urandom

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in vpn-sentinel-cert.csr -signkey vpn-sentinel-key.pem -out vpn-sentinel-cert.pem

# Clean up CSR file
rm vpn-sentinel-cert.csr
rm -f /tmp/.rnd
```

## Using Let's Encrypt Certificates

For production use, obtain certificates from Let's Encrypt:

```bash
# Using certbot
certbot certonly --standalone -d your-domain.com

# Copy certificates to this directory
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./vpn-sentinel-cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./vpn-sentinel-key.pem
```

## Security Notes

- Ensure certificate files have appropriate permissions (600)
- Private key files should be readable only by the owner
- Regularly renew certificates before expiration
- Use strong certificates from trusted CAs for production

## File Permissions

Set correct permissions for certificate files:

```bash
chmod 644 vpn-sentinel-cert.pem
chmod 600 vpn-sentinel-key.pem
```