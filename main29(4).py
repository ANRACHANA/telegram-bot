import os
from pyfiglet import figlet_format
from termcolor import colored

# Get terminal width for centering text
terminal_width = os.get_terminal_size().columns

# Welcome Text
large_text = figlet_format("R A C H A N A", font="slant")
colored_lines = []
for line in large_text.splitlines():
    centered_line = line.center(terminal_width)
    colored_lines.append(colored(centered_line, 'green', attrs=['bold']))

welcome_text = "=== Welcome @ANRACHANA0308 @Telegram Tool for Add Member TG ==="
centered_welcome = welcome_text.center(terminal_width)
colored_welcome = colored(centered_welcome, 'green', attrs=['bold'])

# Print the welcome text with coloring and centering
print("\n".join(colored_lines))
print(colored_welcome)
print("\n\n")

# Your Telegram Bot Script Starts Here
import os
from telethon.errors import UserAlreadyParticipantError, UserPrivacyRestrictedError, FloodWaitError
from telethon.sync import TelegramClient
from telethon.tl.functions.invites import InviteToChannelRequest
from datetime import datetime, timedelta
import asyncio
import pandas as pd

# Load the last processed member from file
def load_last_processed_member():
    if os.path.exists('last_processed_member.txt'):
        with open('last_processed_member.txt', 'r') as file:
            return file.read().strip()  # Read and return the last processed username
    return None  # If file doesn't exist, start from the beginning

# Save the last processed member to file
def save_last_processed_member(username):
    with open('last_processed_member.txt', 'w') as file:
        file.write(username)  # Save the username of the last processed member

# Check if the user is already in the target group
async def is_user_in_group(client, target_group, username):
    participants = await client.get_participants(target_group)
    for participant in participants:
        if participant.username == username:
            return True
    return False

# Main script to add members from one group to another
async def main():
    global log_entries

    # Load account information (replace with actual data)
    accounts_df = pd.read_excel('accounts.xlsx')  # Load from your Excel file
    target_group = 'target_group'  # Replace with the target group name
    source_group = 'source_group'  # Replace with the source group name
    DELAY = 5  # Add delay between actions
    total_accounts = len(accounts_df)
    blacklisted_accounts = set()
    log_entries = []

    # Use the first account to get the target group entity and fetch admin accounts
    scraper = accounts_df.iloc[0]
    client = TelegramClient(f'sessions/{scraper["PHONE"]}', scraper["API_ID"], scraper["API_HASH"])
    await client.start(phone=scraper["PHONE"])

    # Print group names and total members
    source_entity = await client.get_entity(source_group)
    source_members = await client.get_participants(source_entity)
    print(f"\n📦 Source Group: {source_entity.title}")
    print(f"👥 Total Members in Source Group: {len(source_members)}")

    target_entity = await client.get_entity(target_group)
    target_members = await client.get_participants(target_entity)
    print(f"\n🎯 Target Group: {target_entity.title}")
    print(f"👥 Total Members in Target Group: {len(target_members)}")

    # Fetch and display admin accounts in the target group
    admin_accounts = await get_admin_accounts(client, target_entity)
    print(f"\n\n======================\n=== Admin Accounts in Target Group ===")
    print(f"Admin Accounts in Target Group: {len(admin_accounts)}")
    for index, admin in enumerate(admin_accounts, 1):
        print(f"[{index}] [+{admin.phone}] Admin")
    print("======================")

    # Fetch and display non-admin accounts
    non_admin_accounts = [acc for acc in accounts_df.to_dict('records') if acc["PHONE"] not in [admin.phone for admin in admin_accounts]]
    print(f"\n\n======================\n=== Non-Admin Accounts in Target Group ===")
    print(f"Non-Admin Accounts in Target Group: {len(non_admin_accounts)}")
    for index, acc in enumerate(non_admin_accounts, 1):
        print(f"[{index}] [+{acc['PHONE']}] Non-Admin")
    print("======================")

    # Scrape members from the source group
    members_df = await scrape_members(client, source_group)
    await client.disconnect()

    if members_df.empty:
        print(colored("❌ No members found to add.", "red"))
        return

    members_list = members_df.sample(frac=1).to_dict('records')
    account_index = 0
    serial_number = 1  # Initialize serial number for each added member

    # Load the last processed member
    last_processed_member = load_last_processed_member()
    if last_processed_member:
        print(f"Resuming from last processed member: {last_processed_member}")

    # Loop through members and add them to the target group
    for i, member in enumerate(members_list):
        if last_processed_member and member['username'] == last_processed_member:
            continue  # Skip the last processed member

        added = False
        attempts = 0

        while not added and attempts < total_accounts:
            account = accounts_df.iloc[account_index]
            phone = account["PHONE"]
            api_id = account["API_ID"]
            api_hash = account["API_HASH"]

            if phone in blacklisted_accounts:
                print(colored(f"[{phone}] ⛔ Skipped due to previous FloodWait", "red"))
                account_index = (account_index + 1) % total_accounts
                attempts += 1
                continue

            print(colored(f"\n🔁 Trying account [{phone}] to add @{member['username']}", "green"))
            client = TelegramClient(f'sessions/{phone}', api_id, api_hash)

            try:
                await client.start(phone=phone)
                target = await client.get_entity(target_group)
                entity = await client.get_entity(f"@{member['username']}")

                if await is_user_in_group(client, target, member['username']):
                    print(colored(f"[{phone}] ⛔ Already in group: @{member['username']}", "yellow"))
                    log_entries.append({'Username': member['username'], 'Status': 'Already in group', 'Phone': phone,
                                        'Timestamp': datetime.now().strftime("%d/%m/%Y %I:%M %p")})
                    added = True
                    continue

                await client(InviteToChannelRequest(target, [entity]))
                print(colored(f"[{serial_number}] [{phone}] ✅ Successfully added @{member['username']}", "green"))
                log_entries.append({'Username': member['username'], 'Status': 'Added', 'Phone': phone,
                                    'Timestamp': datetime.now().strftime("%d/%m/%Y %I:%M %p")})

                # Save the last processed member after each successful addition
                save_last_processed_member(member['username'])

                if await is_user_in_group(client, target, member['username']):
                    print(colored(f"[{phone}] ✅ Confirmed in group: @{member['username']}", "cyan"))
                else:
                    print(colored(f"[{phone}] ❌ Failed to confirm (maybe kicked): @{member['username']}", "red"))
                    log_entries.append({'Username': member['username'], 'Status': 'Failed to confirm', 'Phone': phone,
                                        'Timestamp': datetime.now().strftime("%d/%m/%Y %I:%M %p")})

                await asyncio.sleep(DELAY)
                added = True
                serial_number += 1  # Increment the serial number after each successful add

            except UserAlreadyParticipantError:
                print(colored(f"[{phone}] ⚠️ Already participant: @{member['username']}", "yellow"))
                log_entries.append({'Username': member['username'], 'Status': 'Already in group', 'Phone': phone,
                                    'Timestamp': datetime.now().strftime("%d/%m/%Y %I:%M %p")})
                added = True

            except UserPrivacyRestrictedError:
                print(colored(f"[{phone}] ❌ Privacy restricted: @{member['username']}", "magenta"))
                log_entries.append({'Username': member['username'], 'Status': 'Privacy restricted', 'Phone': phone,
                                    'Timestamp': datetime.now().strftime("%d/%m/%Y %I:%M %p")})
                added = True

            except FloodWaitError as e:
                wait_time = e.seconds  # the number of seconds to wait
                wait_start_time = datetime.now()
                wait_end_time = wait_start_time + timedelta(seconds=wait_time)
                formatted_start_time = wait_start_time.strftime("%d/%m/%Y %I:%M %p")
                formatted_end_time = wait_end_time.strftime("%d/%m/%Y %I:%M %p")
                
                print(colored(f"[{phone}] 🕒 FloodWait for {wait_time}s (from {formatted_start_time} to {formatted_end_time}), skipping this account", "red"))
                log_entries.append({'Username': member['username'], 'Status': f'FloodWait for {wait_time}s', 'Phone': phone,
                                    'Timestamp': formatted_start_time, 'WaitUntil': formatted_end_time})

                blacklisted_accounts.add(phone)
                added = False
                await asyncio.sleep(wait_time)

            except Exception as e:
                print(colored(f"[{phone}] ⚠️ Error: {e}", "red"))
                log_entries.append({'Username': member['username'], 'Status': 'Error', 'Phone': phone,
                                    'Timestamp': datetime.now().strftime("%d/%m/%Y %I:%M %p")})
                added = False

            await client.disconnect()
            account_index = (account_index + 1) % total_accounts  # Rotate accounts

    # Save logs
    log_df = pd.DataFrame(log_entries)
    log_df.to_excel(f"log_{datetime.now().strftime('%d%m%Y%H%M%S')}.xlsx", index=False)

# Run the main function
asyncio.run(main())
