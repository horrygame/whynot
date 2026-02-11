from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")

# Хранилище: session_id -> {'sid': websocket_sid, 'info': {}}
active_sessions = {}

@app.route('/')
def index():
    """Панель управления оператора"""
    return render_template('control.html', sessions=active_sessions)

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('register')
def handle_register(data):
    """Клиент регистрируется с уникальным ID"""
    session_id = data.get('session_id')
    if session_id:
        active_sessions[session_id] = {
            'sid': request.sid,
            'info': data.get('info', {})
        }
        emit('registered', {'status': 'ok'})
        # Уведомить оператора об обновлении списка
        socketio.emit('sessions_update', list(active_sessions.keys()))

@socketio.on('disconnect')
def handle_disconnect():
    # Удаляем сессию по websocket sid
    to_remove = None
    for sess_id, sess in active_sessions.items():
        if sess['sid'] == request.sid:
            to_remove = sess_id
            break
    if to_remove:
        del active_sessions[to_remove]
        socketio.emit('sessions_update', list(active_sessions.keys()))

@socketio.on('command')
def handle_command(data):
    """Команда от оператора -> пересылается конкретному клиенту"""
    target_session = data.get('session_id')
    cmd = data.get('command')
    payload = data.get('payload', {})
    if target_session in active_sessions:
        target_sid = active_sessions[target_session]['sid']
        emit('command', {'cmd': cmd, 'payload': payload}, room=target_sid)
        emit('command_status', {'status': f'Command sent to {target_session}'})
    else:
        emit('command_status', {'status': 'Session not found'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)  # Render использует порт 10000
