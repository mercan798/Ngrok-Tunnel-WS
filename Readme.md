Siz şunu dediniz:

ingilizce olosun emojisiz olsun ve çok net ve kısa olsun
Gemini şunu dedi:
One Society: Secure Terminal Chat

One Society is a lightweight, FastAPI-powered messaging system featuring a retro-futuristic Terminal User Interface (TUI) built with Textual and Rich. It focuses on privacy through a two-node limit and password-protected rooms.
Features

    Terminal UI: High-contrast HUD interface for secure communication.

    WebSocket Backend: Fast, asynchronous message routing using FastAPI.

    Room Security: Access controlled via .env password and room keys.

    Node Limit: Enforced maximum of 2 users per room for privacy.

    Resource Management: Automatic room cleanup upon user disconnection.

Installation

Install the required dependencies:
Bash

pip install fastapi uvicorn websockets textual rich python-dotenv

Configuration

Create a .env file in the root directory:
Kod snippet'i

ROOM_PASSWORD=your_secure_password

Usage

1. Start the Backend Server:
Bash

uvicorn main:app --reload --port 8000

2. Launch the TUI Client:
Bash

python client.py

Technical Specs

    Backend: FastAPI, Python-dotenv, Uvicorn.

    Frontend: Textual (TUI framework), Rich (Formatting), Websockets (Client).

    Communication: JSON-based data exchange supporting system alerts and file metadata.

    Commands: Use /leave within the chat input to disconnect.

Author

Developed by a software developer  "Mercan Olcek " specializing in Python, FastAPI, and Linux systems.
