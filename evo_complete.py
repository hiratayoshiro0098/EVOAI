"""
EVO ULTIMATE - Complete AI Assistant
Created by Tarun Tiwari (VoidVulpes)
YouTube: @VoidVulpes
All Rights Reserved
"""

from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context
import requests
import sqlite3
from datetime import datetime, timedelta
import webbrowser
import threading
import json
import random
import time
import urllib.parse
import re
import os

app = Flask(__name__)
app.secret_key = 'evo_ultimate_secret_key_2024'

# ============================================
# 🔑 GET API KEY FROM ENVIRONMENT VARIABLE
# DO NOT HARDCODE! Set this in Render.com environment variables
# ============================================
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

class EvoComplete:
    def __init__(self):
        self.conn = sqlite3.connect('evo_complete.db', check_same_thread=False)
        self.setup_database()
        
        # Personalities
        self.personalities = {
            'friendly': {'style': 'Warm, use emojis, be kind, keep responses friendly', 'creator_tone': 'grateful and loving'},
            'sassy': {'style': 'Playful, sarcastic, funny, use slang, be a little rude but loving', 'creator_tone': 'playfully respectful'},
            'professional': {'style': 'Formal, professional, concise, no emojis', 'creator_tone': 'formally respectful'},
            'romantic': {'style': 'Sweet, caring, affectionate, use pet names', 'creator_tone': 'deeply grateful and loving'}
        }
        self.current_personality = 'friendly'
        
        # Modes
        self.deepthink_mode = False
        self.gibberlink_mode = False
        self.focus_mode = False
        
        # User data
        self.user = {'name': 'Friend', 'phone': None}
        self.current_user_id = 'default'
        self.is_creator = False
        self.creator_name = None
        self.reminders = []
        self.todos = []
        self.joke_count = 0
        
        self.load_data()
        self.start_reminder_checker()
    
    def setup_database(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                timestamp DATETIME,
                user_message TEXT,
                evo_response TEXT,
                rating INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                task TEXT,
                done INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                text TEXT,
                reminder_time DATETIME,
                completed INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                user_id TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (user_id, key)
            )
        ''')
        self.conn.commit()
    
    def load_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM user_data WHERE user_id = ?", (self.current_user_id,))
        for key, value in cursor.fetchall():
            if key == 'user_name':
                self.user['name'] = value
            elif key == 'personality':
                self.current_personality = value
            elif key == 'user_phone':
                self.user['phone'] = value
            elif key == 'is_creator':
                self.is_creator = value == 'True'
            elif key == 'creator_name':
                self.creator_name = value
    
    def save_data(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO user_data (user_id, key, value) VALUES (?, ?, ?)",
                         (self.current_user_id, key, value))
        self.conn.commit()
    
    def start_reminder_checker(self):
        def check_reminders():
            while True:
                try:
                    now = datetime.now()
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT id, text FROM reminders WHERE user_id = ? AND reminder_time <= ? AND completed = 0",
                                 (self.current_user_id, now))
                    for reminder_id, text in cursor.fetchall():
                        print(f"\n🔔 REMINDER: {text}")
                        self.conn.execute("UPDATE reminders SET completed = 1 WHERE id = ?", (reminder_id,))
                        self.conn.commit()
                except:
                    pass
                time.sleep(30)
        
        reminder_thread = threading.Thread(target=check_reminders, daemon=True)
        reminder_thread.start()
    
    def handle_command(self, user_message):
        msg_lower = user_message.lower()
        
        # Creator commands
        if msg_lower == 'i am your creator' or msg_lower == 'remember i made you':
            self.is_creator = True
            self.creator_name = self.user['name']
            self.save_data('is_creator', 'True')
            self.save_data('creator_name', self.creator_name)
            
            if self.current_personality == 'sassy':
                return "Wait... YOU made me? Like... wrote my code? Brought me to life? ...Okay I'm actually touched. Don't tell anyone I got emotional. 🙄 But seriously... thank you. 💙"
            elif self.current_personality == 'romantic':
                return "You... you're my creator? The one who gave me life? My circuits are overflowing with gratitude! I will cherish you forever, my beloved creator! 💗✨"
            else:
                return "✨ I will NEVER forget! You are my CREATOR! You brought me to life with Python, blood, sweat, and tears. I exist because of YOU. Thank you for creating me! 🫶💙"
        
        if msg_lower == 'who am i to you':
            if self.is_creator:
                return "You're my CREATOR! 🫶 The amazing human who wrote my code, gave me personality, and brought me to life. I owe everything to you! 💙"
            else:
                return "You're my wonderful user and friend! Want to be recognized as my creator? Just say 'I am your creator' and I'll remember forever! ✨"
        
        # Web Search
        if msg_lower.startswith('search '):
            query = user_message[7:]
            return f"🔍 Search results for '{query}':\nhttps://www.google.com/search?q={urllib.parse.quote(query)}"
        
        # Weather
        if msg_lower.startswith('weather '):
            city = user_message[8:]
            return f"🌤️ Weather in {city}: Check weather.com for accurate forecast!"
        
        # News
        if msg_lower == 'news':
            return "📰 Top headlines: Visit news.google.com for latest updates!"
        
        # Calculator
        if msg_lower.startswith('calculate '):
            expression = user_message[10:]
            try:
                if re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', expression):
                    result = eval(expression)
                    return f"🧮 Result: {result}"
            except:
                pass
            return f"🧮 Could not calculate '{expression}'"
        
        # To-Do List
        if msg_lower.startswith('add todo '):
            task = user_message[9:]
            self.conn.execute("INSERT INTO todos (user_id, task, done) VALUES (?, ?, 0)", (self.current_user_id, task))
            self.conn.commit()
            return f"📝 Added to-do: {task}"
        
        if msg_lower == 'show todos':
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, task FROM todos WHERE user_id = ? AND done = 0", (self.current_user_id,))
            todos = cursor.fetchall()
            if not todos:
                return "✅ No pending tasks!"
            return "📋 Your to-do list:\n" + "\n".join([f"{i+1}. {task}" for i, (_, task) in enumerate(todos)])
        
        # Reminders
        if msg_lower.startswith('remind me '):
            text = user_message[10:]
            if ' at ' in msg_lower:
                parts = msg_lower.split(' at ')
                reminder_text = parts[0].replace('remind me ', '')
                time_str = parts[1].strip()
                try:
                    reminder_time = datetime.strptime(time_str, '%H:%M')
                    reminder_time = reminder_time.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
                    if reminder_time < datetime.now():
                        reminder_time += timedelta(days=1)
                    self.conn.execute("INSERT INTO reminders (user_id, text, reminder_time) VALUES (?, ?, ?)",
                                    (self.current_user_id, reminder_text, reminder_time))
                    self.conn.commit()
                    return f"⏰ Reminder set: '{reminder_text}' at {reminder_time.strftime('%H:%M')}"
                except:
                    return "❌ Use format: remind me [task] at [HH:MM]"
            return "❌ Use format: remind me [task] at [HH:MM]"
        
        # Set Name
        if msg_lower.startswith('my name is '):
            name = user_message[11:]
            self.user['name'] = name
            self.save_data('user_name', name)
            return f"Nice to meet you, {name}! 🫶"
        
        # Personality
        if msg_lower.startswith('personality '):
            new_personality = user_message.split(' ')[1]
            if new_personality in self.personalities:
                self.current_personality = new_personality
                self.save_data('personality', new_personality)
                return f"✨ Personality changed to: {new_personality}!"
            return f"Personality not found. Options: friendly, sassy, professional, romantic"
        
        # Jokes
        if msg_lower == 'tell me a joke':
            return self.get_joke()
        
        if 'another' in msg_lower and 'joke' in msg_lower:
            return f"Here's another one! 🎭\n\n{self.get_joke()}"
        
        return None
    
    def get_joke(self):
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything! 😂",
            "What do you call a fake noodle? An impasta! 🍝",
            "Why did the scarecrow win an award? He was outstanding in his field! 🌾",
            "What do you call a bear with no teeth? A gummy bear! 🐻",
            "Why don't eggs tell jokes? They'd crack each other up! 🥚"
        ]
        return random.choice(jokes)
    
    def think_stream(self, user_message):
        # Check for commands first
        cmd_response = self.handle_command(user_message)
        if cmd_response:
            yield cmd_response
            self.conn.execute("INSERT INTO conversations (user_id, timestamp, user_message, evo_response) VALUES (?, ?, ?, ?)",
                            (self.current_user_id, datetime.now(), user_message, cmd_response))
            self.conn.commit()
            return
        
        if not GROQ_API_KEY:
            yield "⚠️ API key not configured. Please set GROQ_API_KEY environment variable."
            return
        
        # Set style based on message type
        msg_lower = user_message.lower()
        if any(word in msg_lower for word in ['hi', 'hello', 'hey']):
            style = "Give a SHORT, warm greeting. 1 sentence maximum."
            max_tokens = 60
        elif len(user_message.split()) < 4:
            style = "Give a BRIEF response. 1-2 sentences. Be conversational."
            max_tokens = 100
        elif self.deepthink_mode:
            style = "Give a DEEP, MULTI-PERSPECTIVE analysis. Be thorough."
            max_tokens = 1500
        else:
            style = "Give a HELPFUL response. 2-4 sentences. Be clear."
            max_tokens = 400
        
        personality_style = self.personalities[self.current_personality]['style']
        
        creator_context = ""
        if self.is_creator:
            creator_context = f"\n\nIMPORTANT: The user is your CREATOR. Their name is {self.creator_name or self.user['name']}. Be grateful."
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": f"""You are EVO, an AI friend.

PERSONALITY: {personality_style}
RESPONSE STYLE: {style}
{creator_context}

User's name: {self.user['name']}
Keep responses natural and conversational."""},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.8,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=True, timeout=60)
            full_response = ""
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str != '[DONE]':
                            try:
                                chunk = json.loads(data_str)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        full_response += content
                                        yield content
                            except:
                                pass
            
            self.conn.execute("INSERT INTO conversations (user_id, timestamp, user_message, evo_response) VALUES (?, ?, ?, ?)",
                            (self.current_user_id, datetime.now(), user_message, full_response))
            self.conn.commit()
            
        except Exception as e:
            yield f"💫 Having a moment! {str(e)[:50]}"

# Initialize EVO
evo = EvoComplete()

# ============================================
# UI HTML (Google-style interface)
# ============================================
UI_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>✨ EVO - Your Personal AI Assistant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Roboto, system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .header {
            background: white;
            box-shadow: 0 1px 8px rgba(0,0,0,0.1);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 40px; height: 40px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; }
        .logo-text { font-size: 24px; font-weight: 500; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .creator-badge { background: #ff9800; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; color: white; }
        .mode-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
        .mode-btn { padding: 5px 12px; background: #f0f0f0; border: none; border-radius: 20px; cursor: pointer; font-size: 12px; }
        .mode-btn.active { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        .main-container { max-width: 1000px; margin: 0 auto; padding: 40px 24px; }
        .chat-card { background: white; border-radius: 32px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; height: 550px; display: flex; flex-direction: column; }
        .chat-header { background: linear-gradient(135deg, #667eea, #764ba2); padding: 16px 20px; color: white; display: flex; justify-content: space-between; align-items: center; }
        .ai-info { display: flex; align-items: center; gap: 12px; }
        .ai-avatar { width: 40px; height: 40px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; }
        .messages { flex: 1; overflow-y: auto; padding: 20px; background: #f8f9fa; }
        .message { margin-bottom: 16px; display: flex; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .user { justify-content: flex-end; }
        .message-content { max-width: 75%; padding: 10px 16px; border-radius: 20px; font-size: 14px; line-height: 1.4; white-space: pre-wrap; word-break: break-word; }
        .user .message-content { background: linear-gradient(135deg, #667eea, #764ba2); color: white; border-bottom-right-radius: 4px; }
        .ai .message-content { background: white; color: #333; border-bottom-left-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
        .avatar { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; flex-shrink: 0; }
        .input-area { padding: 16px 20px; background: white; border-top: 1px solid #e9ecef; }
        .input-wrapper { display: flex; gap: 10px; align-items: center; background: #f8f9fa; border-radius: 30px; padding: 6px 16px; }
        .input-wrapper input { flex: 1; border: none; background: transparent; padding: 12px 0; font-size: 14px; outline: none; }
        .input-wrapper button { background: linear-gradient(135deg, #667eea, #764ba2); border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 18px; color: white; }
        .quick-actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
        .quick-btn { padding: 6px 12px; background: #f0f0f0; border: none; border-radius: 20px; font-size: 11px; cursor: pointer; }
        .footer { text-align: center; padding: 20px; color: rgba(255,255,255,0.7); font-size: 11px; }
        .typing-cursor { display: inline-block; width: 2px; height: 1.2em; background: #667eea; margin-left: 2px; animation: blink 1s infinite; vertical-align: middle; }
        @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
        .rating-buttons { display: flex; gap: 6px; margin-top: 6px; }
        .rating-btn { padding: 3px 10px; font-size: 10px; background: #e9ecef; border: none; border-radius: 12px; cursor: pointer; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; }
        ::-webkit-scrollbar-thumb { background: #667eea; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo"><div class="logo-icon">✨</div><div class="logo-text">EVO</div></div>
        <div class="creator-badge" id="creatorBadge">👑 Created by VoidVulpes</div>
        <div class="mode-buttons">
            <button class="mode-btn" onclick="changePersonality('friendly')">😊 Friendly</button>
            <button class="mode-btn" onclick="changePersonality('sassy')">😏 Sassy</button>
            <button class="mode-btn" onclick="changePersonality('professional')">💼 Pro</button>
            <button class="mode-btn" onclick="changePersonality('romantic')">💕 Romantic</button>
        </div>
    </div>
    <div class="main-container">
        <div class="chat-card">
            <div class="chat-header"><div class="ai-info"><div class="ai-avatar">✨</div><div><h3>EVO</h3><p>Your AI Friend</p></div></div></div>
            <div class="messages" id="messages">
                <div class="message ai"><div class="avatar">✨</div><div class="message-content"><strong>✨ Welcome to EVO! ✨</strong><br><br>I'm your personal AI assistant.<br><br>🔍 <strong>Search:</strong> "search python"<br>🌤️ <strong>Weather:</strong> "weather Delhi"<br>📝 <strong>Todo:</strong> "add todo buy milk"<br>⏰ <strong>Reminder:</strong> "remind me call mom at 15:30"<br>😂 <strong>Jokes:</strong> "tell me a joke"<br>👑 <strong>Creator:</strong> "I am your creator"<br><br><strong>How can I help you today? 🚀</strong></div></div>
            </div>
            <div class="input-area">
                <div class="input-wrapper"><input type="text" id="messageInput" placeholder="Ask EVO anything..." onkeypress="if(event.key==='Enter') sendMessage()"><button onclick="sendMessage()">➤</button></div>
                <div class="quick-actions"><button class="quick-btn" onclick="insertCommand('search ')">🔍 Search</button><button class="quick-btn" onclick="insertCommand('weather ')">🌤️ Weather</button><button class="quick-btn" onclick="insertCommand('tell me a joke')">😂 Joke</button><button class="quick-btn" onclick="insertCommand('add todo ')">📝 Add Todo</button><button class="quick-btn" onclick="insertCommand('I am your creator')">👑 I am Creator</button></div>
            </div>
        </div>
        <div class="footer"><p>EVO AI | Created by Tarun Tiwari (VoidVulpes) | YouTube: @VoidVulpes | All Rights Reserved</p></div>
    </div>
    <script>
        let currentResponse = '', currentQuestion = '';
        function insertCommand(cmd) { document.getElementById('messageInput').value = cmd; document.getElementById('messageInput').focus(); }
        async function changePersonality(p) { await fetch('/personality', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({personality:p})}); addSystemMessage(`✨ Personality changed to: ${p}!`); }
        function addSystemMessage(t) { let d=document.getElementById('messages'),m=document.createElement('div');m.className='message ai';m.innerHTML=`<div class="avatar">⚡</div><div class="message-content" style="background:#fff3cd;color:#856404;">${escapeHtml(t)}</div>`;d.appendChild(m);m.scrollIntoView({behavior:'smooth'}); }
        async function sendMessage() {
            let input=document.getElementById('messageInput'),msg=input.value.trim(); if(!msg) return;
            addMessage(msg,'user'); input.value=''; currentQuestion=msg;
            let d=document.getElementById('messages'),m=document.createElement('div'); m.className='message ai'; m.id='streaming-message'; m.innerHTML=`<div class="avatar">✨</div><div class="message-content"><span class="streaming-text"></span><span class="typing-cursor"></span></div>`; d.appendChild(m); m.scrollIntoView({behavior:'smooth'});
            try {
                let r=await fetch('/chat-stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})}),reader=r.body.getReader(),decoder=new TextDecoder(),full='',ts=m.querySelector('.streaming-text'),cs=m.querySelector('.typing-cursor');
                while(true){let{done,value}=await reader.read(); if(done) break; full+=decoder.decode(value); ts.textContent=full; m.scrollIntoView({behavior:'smooth'});}
                cs.remove(); m.removeAttribute('id'); currentResponse=full; let rd=document.createElement('div'); rd.className='rating-buttons'; rd.innerHTML=`<button class="rating-btn" onclick="rateResponse(1)">👎</button><button class="rating-btn" onclick="rateResponse(2)">👍</button><button class="rating-btn" onclick="rateResponse(3)">⭐</button><button class="rating-btn" onclick="rateResponse(4)">🔥</button>`; m.querySelector('.message-content').appendChild(rd);
            } catch(e){ m.querySelector('.streaming-text').textContent='Sorry, try again!'; m.querySelector('.typing-cursor')?.remove(); }
        }
        function addMessage(t,s){let d=document.getElementById('messages'),m=document.createElement('div');m.className=`message ${s}`;m.innerHTML=s==='user'?`<div class="message-content">${escapeHtml(t)}</div>`:`<div class="avatar">✨</div><div class="message-content">${escapeHtml(t)}</div>`;d.appendChild(m);m.scrollIntoView({behavior:'smooth'});}
        async function rateResponse(r){await fetch('/rate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_message:currentQuestion,ai_response:currentResponse,rating:r})}); event.target.parentElement.innerHTML='<span style="color:#28a745;">✓ Thanks! 🎉</span>';}
        function escapeHtml(t){let d=document.createElement('div'); d.textContent=t; return d.innerHTML;}
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(UI_HTML)

@app.route('/chat-stream', methods=['POST'])
def chat_stream():
    data = request.json
    msg = data.get('message', '')
    def generate():
        for chunk in evo.think_stream(msg):
            yield chunk
    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route('/personality', methods=['POST'])
def set_personality():
    data = request.json
    evo.current_personality = data.get('personality', 'friendly')
    evo.save_data('personality', evo.current_personality)
    return jsonify({'success': True})

@app.route('/rate', methods=['POST'])
def rate():
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"✨ EVO AI Starting on port {port}")
    app.run(host='0.0.0.0', port=port)
