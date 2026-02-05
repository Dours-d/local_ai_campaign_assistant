
import os
import json
import hashlib
import base58
from eth_account import Account
from dotenv import load_dotenv

# Allow HD Wallet features (required for derivation from mnemonic)
Account.enable_unaudited_hdwallet_features()

VAULT_MAPPING = "data/vault_mapping.json"
DOTENV_PATH = ".env"

class SovereignVault:
    def __init__(self):
        load_dotenv(DOTENV_PATH)
        self.mnemonic = os.getenv("VAULT_MNEMONIC")
        
        if not self.mnemonic:
            # Generate a new secure mnemonic if none exists
            print("!!! NO VAULT MNEMONIC FOUND !!!")
            print("Generating a new Sovereign Root. This is the master key for all beneficiary funds.")
            new_acct, mnemonic = Account.create_with_mnemonic()
            self.mnemonic = mnemonic
            
            # Save to .env
            with open(DOTENV_PATH, "a") as f:
                if os.path.getsize(DOTENV_PATH) > 0:
                    f.write("\n")
                f.write(f"VAULT_MNEMONIC=\"{self.mnemonic}\"")
            
            print("--- IMPORTANT: SAVE THIS MNEMONIC SECURELY ---")
            print(f"ROOT_SEED: {self.mnemonic}")
            print("---------------------------------------------")

        self.mapping = {}
        if os.path.exists(VAULT_MAPPING):
            try:
                with open(VAULT_MAPPING, 'r') as f:
                    self.mapping = json.load(f)
            except (json.JSONDecodeError, StopIteration):
                self.mapping = {}

    def eth_to_tron(self, eth_address):
        """Converts an Ethereum-style 0x address to a TRON address."""
        address_bytes = bytes.fromhex(eth_address[2:])
        prefixed_address = b'\x41' + address_bytes
        checksum = hashlib.sha256(hashlib.sha256(prefixed_address).digest()).digest()[:4]
        return base58.b58encode(prefixed_address + checksum).decode()

    def get_address(self, beneficiary_id):
        """
        Returns a unique, provisioned USDT address for a beneficiary.
        """
        if beneficiary_id in self.mapping:
            return self.mapping[beneficiary_id]["address"]
        return None

    def register_external_address(self, beneficiary_id, address):
        """
        Manually register an existing self-custody address for a beneficiary.
        """
        self.mapping[beneficiary_id] = {
            "address": address,
            "status": "Self-Custody",
            "network": "USDT-TRC20-External"
        }
        self.save_mapping()

    def provision_new_address(self, beneficiary_id):
        """
        Derives a new TRON HD wallet address at the next available index.
        Uses the standard BIP44 path for TRON: m/44'/195'/0'/0/index
        """
        if beneficiary_id in self.mapping:
            return self.mapping[beneficiary_id]["address"]

        # Derive new address at the next available index
        index = len(self.mapping)
        path = f"m/44'/195'/0'/0/{index}"
        
        try:
            # We use eth_account to derive the key, then format it as TRON
            acct = Account.from_mnemonic(self.mnemonic, account_path=path)
            tron_address = self.eth_to_tron(acct.address)
            
            self.mapping[beneficiary_id] = {
                "address": tron_address,
                "eth_compat_address": acct.address, # Keep for internal reference
                "index": index,
                "path": path,
                "status": "Provisional",
                "network": "USDT-TRC20"
            }
            self.save_mapping()
            return tron_address
        except Exception as e:
            print(f"Error deriving TRON address: {e}")
            return None

    def save_mapping(self):
        os.makedirs(os.path.dirname(VAULT_MAPPING), exist_ok=True)
        with open(VAULT_MAPPING, 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, indent=2)

if __name__ == "__main__":
    vault = SovereignVault()
    print("Sovereign Vault Initialized for TRON/TRC20.")
