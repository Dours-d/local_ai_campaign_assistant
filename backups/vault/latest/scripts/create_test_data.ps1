<#
.SYNOPSIS
    Generates mock WhatsApp extraction data to verify the Trustee Intelligence system.
#>

$TestFile = Join-Path $PSScriptRoot "..\data\test_intelligence.csv"

# [Timestamp, PhoneNumber, WhatsID, Sender, Message, ChatName]
$Data = @(
    # Header
    "Timestamp,PhoneNumber,WhatsID,Sender,Message,ChatName"
    
    # 1. Valid TRC20 (Cold Wallet) - No illegal Base58 chars (0, O, I, l)
    '"2026-01-30 10:00:00","351937063222","351937063222@c.us","Gael","My cold wallet address is Txyz123456789212345678921234567892. Use this.","Technical Test Chat"'
    
    # 2. Valid ERC20 (Hot Wallet)
    '"2026-01-30 10:05:00","351937063222","351937063222@c.us","Gael","My hot wallet is 0xabcdef1234567890abcdef1234567890abcdef12. Keep it safe.","Technical Test Chat"'
    
    # 3. Valid ERC20 (Custodial - Binance)
    '"2026-01-30 10:10:00","970591234567","970591234567@c.us","Donor","I sent it to the Binance address: 0xabcdef1234567890abcdef1234567890abcdef12.","Donation Chat"'
    
    # 4. ORPHANED Data (No WhatsID) - Should be scrapped
    '"2026-01-30 10:15:00","UNKNOWN","","Ghost","Here is my wallet TorphanedAddress1234567890123456789","Ghost Chat"'
    
    # 5. INVALID TRC20 (Illegal characters '0') - Should be scrapped
    '"2026-01-30 10:20:00","351937063222","351937063222@c.us","Gael","Oops, I sent a typo: TO1l0InvalidAddress12345678901234","Technical Test Chat"'
)

$Data | Out-File -FilePath $TestFile -Encoding utf8
Write-Host "[Test Data Updated] -> $TestFile" -ForegroundColor Green
