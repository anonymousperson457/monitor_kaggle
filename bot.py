import urllib.request
import json
import time
import subprocess
import sys

# Function to fetch JSON from URL
def fetch_json(url):
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

# Function to extract compressed public key from scriptsig hex (P2PKH format: <sig_len><sig><pubkey_len><pubkey>)
def extract_pubkey_from_scriptsig(scriptsig_hex):
    if not scriptsig_hex:
        return None
    scriptsig_bytes = bytes.fromhex(scriptsig_hex)
    if len(scriptsig_bytes) < 2:
        return None
    sig_len = scriptsig_bytes[0]
    if len(scriptsig_bytes) < 1 + sig_len + 1:
        return None
    pubkey_len = scriptsig_bytes[1 + sig_len]
    if len(scriptsig_bytes) < 1 + sig_len + 1 + pubkey_len:
        return None
    pubkey_bytes = scriptsig_bytes[1 + sig_len + 1:1 + sig_len + 1 + pubkey_len]
    # Only accept compressed pubkeys (33 bytes, starting with 02 or 03)
    if len(pubkey_bytes) != 33 or pubkey_bytes[0] not in (0x02, 0x03):
        return None
    return pubkey_bytes.hex()

# Main function
def main():
    # Get user input for the address
    address = input("Enter the Testnet4 P2PKH address to monitor: ").strip()
    if not address:
        print("No address provided. Exiting.")
        sys.exit(1)
    
    api_base = "https://mempool.space/testnet4/api"
    txs_url = f"{api_base}/address/{address}/txs"
    
    print(f"Monitoring address: {address}")
    print("Polling every 3 seconds for a spending transaction to extract compressed public key...")
    
    seen_txids = set()  # Track seen transactions to avoid re-processing
    
    while True:
        txs = fetch_json(txs_url)
        if not txs:
            time.sleep(3)
            continue
        
        for tx in txs:
            txid = tx['txid']
            if txid in seen_txids:
                continue
            seen_txids.add(txid)
            
            for vin in tx['vin']:
                prevout = vin.get('prevout', {})
                if prevout.get('scriptpubkey_address') == address and prevout.get('scriptpubkey_type') == 'p2pkh':
                    pubkey = extract_pubkey_from_scriptsig(vin.get('scriptsig', ''))
                    if pubkey:
                        print(f"Compressed public key found in tx {txid}: {pubkey}")
                        # Ensure kangaroo is executable
                        try:
                            subprocess.run(['chmod', '+x', 'kangaroo'], check=True)
                            print("Set executable permissions for kangaroo")
                        except subprocess.CalledProcessError as e:
                            print(f"Failed to set permissions: {e}")
                            sys.exit(1)
                        # Run the kangaroo command
                        command = ['./kangaroo', '-dp', '14', '-range', '71', '-start', '3fffffffffffffffff', '-pubkey', pubkey]
                        print(f"Executing: {' '.join(command)}")
                        try:
                            subprocess.run(command, check=True)
                        except subprocess.CalledProcessError as e:
                            print(f"Command failed: {e}")
                        sys.exit(0)  # Exit after running
        
        time.sleep(3)

if __name__ == "__main__":
    main()
