import asyncio
from pyrogram import Client

async def main():
    print("--- Pyrogram String Session Generator ---")
    api_id = input("Enter your API ID: ").strip()
    api_hash = input("Enter your API HASH: ").strip()
    
    if not api_id or not api_hash:
        print("API ID and API HASH are required!")
        return

    async with Client(":memory:", api_id=int(api_id), api_hash=api_hash) as app:
        session_string = await app.export_session_string()
        print("\nYour Pyrogram Session String:")
        print("-" * 50)
        print(session_string)
        print("-" * 50)
        print("\nCopy this string and paste it into config.py as USER_SESSION_STRING.")

if __name__ == "__main__":
    asyncio.run(main())
