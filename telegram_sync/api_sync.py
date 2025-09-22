from fastapi import FastAPI, BackgroundTasks
import asyncio
from telegram_sync.sync_chats import main as sync_chats_main
from telegram_sync.sync_messages import main as sync_messages_main

app = FastAPI()

@app.post("/telegram-chats")
async def trigger_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(asyncio.run, sync_chats_main())
    return {"status": "Sync started in background"}

@app.post("/telegram-messages")
async def trigger_sync(full: bool = False, session_file: str = None, chat_id: int = None, background_tasks: BackgroundTasks = None):
    background_tasks.add_task(asyncio.run, sync_messages_main(full_sync=full, session_files=[session_file], chat_id=chat_id))
    return {"status": "Sync started in background", "full_sync": full}