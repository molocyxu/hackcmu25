import sys
import json
import whisper
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEL = None
MODEL_NAME = None

def load_model(model_name):
    global MODEL, MODEL_NAME
    if MODEL is None or MODEL_NAME != model_name:
        MODEL = whisper.load_model(model_name)
        MODEL_NAME = model_name

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/load':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            model_name = data.get('model', 'base')
            try:
                load_model(model_name)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'loaded': True}).encode())
            except Exception as e:
                print("Error in /transcribe load:", e)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'loaded': False, 'error': str(e)}).encode())
        elif self.path == '/transcribe':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            file_path = data.get('audio_path') or data.get('audioPath')
            if file_path is None:
                raise ValueError("No audio_path or audioPath provided in request")
            model_name = data.get('model', 'base')
            try:
                load_model(model_name)
                result = MODEL.transcribe(file_path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, 'text': result['text'], 'language': result.get('language', 'en')}).encode())
            except Exception as e:
                print("Error in /transcribe:", e)
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run():
    server = HTTPServer(('localhost', 8765), Handler)
    print('Whisper server running on port 8765')
    server.serve_forever()

if __name__ == '__main__':
    run()