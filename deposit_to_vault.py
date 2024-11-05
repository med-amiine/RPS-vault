from web3 import Web3
from decimal import Decimal
import json


class USDCVault:
    def __init__(self, web3, vault_address):
        self.web3 = web3

        # Load ABIs from files
        with open('rps_vault_abi.json', 'r') as f:
            vault_abi = json.load(f)

        # Initialize vault contract
        self.vault = web3.eth.contract(address=vault_address, abi=vault_abi)

        # Get USDC address from vault and initialize USDC contract
        self.usdc_address = self.vault.functions.usdc().call()

        # Load USDC ABI
        with open('usdc_abi.json', 'r') as f:
            usdc_abi = json.load(f)
        self.usdc = web3.eth.contract(address=self.usdc_address, abi=usdc_abi)

        # USDC has 6 decimals
        self.USDC_DECIMALS = 6

    def check_deposit_allowance(self, from_address: str, amount_wei: int) -> bool:
        """Check if vault has allowance to spend user's USDC"""
        allowance = self.usdc.functions.allowance(
            from_address,
            self.vault.address
        ).call()
        return allowance >= amount_wei

    def approve_usdc(self, from_address: str, amount_wei: int, private_key: str) -> dict:
        """Approve vault to spend USDC"""
        approve_tx = self.usdc.functions.approve(
            self.vault.address,
            amount_wei
        ).build_transaction({
            'from': from_address,
            'nonce': self.web3.eth.get_transaction_count(from_address),
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price
        })

        signed_tx = self.web3.eth.account.sign_transaction(approve_tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def deposit(self, amount_usdc: Decimal, from_address: str, private_key: str) -> dict:
        """
        Deposit USDC into the vault

        Args:
            amount_usdc: Amount of USDC to deposit (in human readable format)
            from_address: Address making the deposit
            private_key: Private key for signing transactions
        """
        # Convert amount to USDC decimals
        amount_wei = int(amount_usdc * Decimal(10 ** self.USDC_DECIMALS))

        # Check USDC balance
        balance = self.usdc.functions.balanceOf(from_address).call()
        if balance < amount_wei:
            raise ValueError(f"Insufficient USDC balance. Have {balance / 10 ** 6} USDC, need {amount_usdc} USDC")

        # Check and handle USDC approval if needed
        if not self.check_deposit_allowance(from_address, amount_wei):
            print("Approving USDC...")
            self.approve_usdc(from_address, amount_wei, private_key)
            print("USDC approved!")

        # Build deposit transaction
        deposit_tx = self.vault.functions.deposit(
            amount_wei,
            from_address
        ).build_transaction({
            'from': from_address,
            'nonce': self.web3.eth.get_transaction_count(from_address),
            'gas': 500000,
            'gasPrice': self.web3.eth.gas_price
        })

        # Sign and send deposit transaction
        signed_tx = self.web3.eth.account.sign_transaction(deposit_tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def get_metrics(self, address: str) -> dict:
        """Get key vault metrics for an address"""
        return {
            'total_assets': self.vault.functions.totalAssets().call() / 10 ** self.USDC_DECIMALS,
            'max_deposit': self.vault.functions.maxDeposit(address).call() / 10 ** self.USDC_DECIMALS,
            'balance': self.vault.functions.balanceOf(address).call(),
            'latest_value': self.vault.functions.latestVaultValue().call() / 10 ** self.USDC_DECIMALS,
            'invested_amount': self.vault.functions.currentVaultFundsInvestedAmount().call() / 10 ** self.USDC_DECIMALS
        }


def main():

    # Initialize Web3 connection
    w3 = Web3(Web3.HTTPProvider('https://mainnet.mode.network/'))

    # Contract addresses
    VAULT_ADDRESS = '0xCDe9ab402F1951E8A447f83E9D57Fa2F00CDC516'

    # Initialize vault contract
    vault = USDCVault(w3, VAULT_ADDRESS)

    # Your wallet details
    FROM_ADDRESS = ''
    PRIVATE_KEY = ''

    # Initialize vault
    vault = USDCVault(w3, VAULT_ADDRESS)

    try:
        # Get metrics before deposit
        print("\nMetrics before deposit:")
        metrics = vault.get_metrics(FROM_ADDRESS)
        for key, value in metrics.items():
            print(f"{key}: {value}")

        # Amount to deposit (in USDC)
        DEPOSIT_AMOUNT = Decimal('0.001')  # Change this to deposit different amount

        print(f"\nDepositing {DEPOSIT_AMOUNT} USDC...")
        receipt = vault.deposit(DEPOSIT_AMOUNT, FROM_ADDRESS, PRIVATE_KEY)
        print(f"Deposit successful! Transaction hash: {receipt['transactionHash'].hex()}")

        # Get metrics after deposit
        print("\nMetrics after deposit:")
        metrics = vault.get_metrics(FROM_ADDRESS)
        for key, value in metrics.items():
            print(f"{key}: {value}")

    except Exception as e:
        print(f"Error during deposit: {e}")


if __name__ == "__main__":
    main()

