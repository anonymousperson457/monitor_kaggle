import urllib.request
import json
import time
import subprocess
import sys

def fetch_json(url):
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Error Fetching {url}: {e}")
        return None

def extract_pubkey_from_scriptsig(scriptsig_hex):
    if not scriptsig_hex:
        return None
    try:
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
        if len(pubkey_bytes) != 33 or pubkey_bytes[0] not in (0x02, 0x03):
            return None
        return pubkey_bytes.hex()
    except ValueError:
        return None

def main():
    address = "1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
    if not address.startswith('1'):
        print("Invalid P2PKH Address (Must Start With '1'). Exiting.")
        sys.exit(1)
    
    api_base = "https://mempool.space/api"
    txs_url = f"{api_base}/address/{address}/txs"
    
    print(f"Monitoring Address For Outgoing Tx: {address}")
    print("Checking For Outgoing Tx To Extract Public Key...")
    
    seen_txids = set()
    
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
            
            is_outgoing = False
            for vin in tx['vin']:
                prevout = vin.get('prevout', {})
                if prevout.get('scriptpubkey_address') == address and prevout.get('scriptpubkey_type') == 'p2pkh':
                    is_outgoing = True
                    pubkey = extract_pubkey_from_scriptsig(vin.get('scriptsig', ''))
                    if pubkey:
                        print("Public Key Found")
                        try:
                            subprocess.run(['chmod', '+x', 'kangaroo'], check=True)
                            print("Set Executable Permissions For kangaroo")
                        except subprocess.CalledProcessError as e:
                            print(f"Failed To Set Permissions: {e}")
                            sys.exit(1)
                        command = ['./kangaroo', '-dp', '14', '-range', '71', '-start', '3fffffffffffffffff', '-pubkey', pubkey]
                        print(f"Executing: {' '.join(command)}")
                        try:
                            subprocess.run(command, check=True)
                        except subprocess.CalledProcessError as e:
                            print(f"Command failed: {e}")
                        sys.exit(0)
        time.sleep(3)

if __name__ == "__main__":
    main()
