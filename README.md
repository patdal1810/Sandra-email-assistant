# Sandra Email Assistant 

Sandra is an AI-Agent Gmail assistant that reads your inbox, classifies emails by importance, and safely drafts or sends replies on your behalf.

This project combines:
- Gmail API – read, reply, and send emails from your Gmail account  
- OpenAI (GPT-4.1-mini) – classify and generate human-like email responses  
- Rule-based guards – avoid replying to no-reply/system messages  
- CLI tools – watch your inbox or compose mood‑aware emails interactively  

##  Features
- Unread inbox scan (`main.py`)
- AI Email Butler (`agent_sandra.py`)
- AI Email Composer (mood‑aware)
- Inbox watcher (`watch.py`)
- Interactive email sending

##  Project Structure
```
SANDRA-EMAIL-ASSISTANT/
├─ .env
├─ agent_sandra.py
├─ config.py
├─ credentials.json
├─ gmail_client.py
├─ main.py
├─ reply_guard.py
├─ rules.py
├─ state.json
├─ state.py
├─ token.json
├─ watch.py
└─ venv/
```

## Getting Started
1. Clone repo  
2. Create virtual environment  
3. Install dependencies  
4. Configure `.env`  
5. Enable Gmail API  

## Running
```
python main.py        # One‑shot inbox scan
python watch.py       # Watch inbox or compose email
```

## Requirements
See requirements.txt:
- openai  
- python-dotenv  
- google-api-python-client  
- google-auth  
- google-auth-oauthlib  

## Roadmap
- Web dashboard  
- Push notifications  
- Domain-level rule configuration  

## License
MIT License
