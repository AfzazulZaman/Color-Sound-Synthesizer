from flask import Flask, request, jsonify, render_template_string
import uuid
import json
import os

app = Flask(__name__)
SEQUENCE_STORE = "sequences"

# Ensure storage folder exists
if not os.path.exists(SEQUENCE_STORE):
    os.makedirs(SEQUENCE_STORE)

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Color-Sound Synthesizer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #111;
            color: #fff;
            margin: 0;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            margin: 20px;
            color: #0ff;
        }
        canvas {
            background-color: #222;
            border: 2px solid #0ff;
            margin: 10px;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        button, select {
            padding: 10px;
            font-size: 14px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #333;
        }
        select {
            background: #000;
            color: #0ff;
        }
    </style>
</head>
<body>
    <h1>Color-Sound Synthesizer</h1>
    <div class="controls">
        <select id="waveform">
            <option value="sine">Sine</option>
            <option value="square">Square</option>
            <option value="triangle">Triangle</option>
            <option value="sawtooth">Sawtooth</option>
        </select>
        <button onclick="startRecording()">Start Recording</button>
        <button onclick="stopRecording()">Stop Recording</button>
        <button onclick="playRecording()">Play Recording</button>
        <button onclick="saveRecording()">Save</button>
        <input type="text" id="loadId" placeholder="Enter ID to load">
        <button onclick="loadRecording()">Load</button>
    </div>
    <canvas id="visuals" width="800" height="400"></canvas>

    <script>
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const attackTime = 0.05;
        const releaseTime = 0.3;
        let waveform = "sine";

        const keyToFreq = {
            "A": 261.63, "S": 293.66, "D": 329.63,
            "F": 349.23, "G": 392.00, "H": 440.00,
            "J": 493.88, "K": 523.25, "L": 587.33,
            "Q": 659.25, "W": 698.46, "E": 783.99,
            "R": 880.00, "T": 987.77, "Y": 1046.50,
            "U": 1174.66, "I": 1318.51
        };

        const activeOscillators = {};
        const canvas = document.getElementById("visuals");
        const ctx = canvas.getContext("2d");

        function drawShape(x, y, color) {
            ctx.beginPath();
            ctx.arc(x, y, 20, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
        }

        function randomColor() {
            return `hsl(${Math.floor(Math.random() * 360)}, 100%, 50%)`;
        }

        function playNote(freq, key) {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = waveform;
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(0, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(1, audioCtx.currentTime + attackTime);
            gain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + attackTime + releaseTime);

            osc.connect(gain).connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + attackTime + releaseTime);

            activeOscillators[key] = osc;

            const x = Math.random() * canvas.width;
            const y = Math.random() * canvas.height;
            drawShape(x, y, randomColor());
        }

        document.addEventListener("keydown", e => {
            const key = e.key.toUpperCase();
            if (keyToFreq[key] && !activeOscillators[key]) {
                playNote(keyToFreq[key], key);
                if (isRecording) {
                    recording.push({ key, time: Date.now() - recordStart });
                }
            }
        });

        document.getElementById("waveform").addEventListener("change", e => {
            waveform = e.target.value;
        });

        // Recording Logic
        let isRecording = false;
        let recordStart = 0;
        let recording = [];

        function startRecording() {
            isRecording = true;
            recordStart = Date.now();
            recording = [];
        }

        function stopRecording() {
            isRecording = false;
            alert("Recording stopped. You can now play, save or load.");
        }

        function playRecording() {
            if (!recording.length) return alert("No recording to play.");
            for (let note of recording) {
                setTimeout(() => {
                    playNote(keyToFreq[note.key], note.key);
                }, note.time);
            }
        }

        function saveRecording() {
            fetch('/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(recording)
            })
            .then(res => res.json())
            .then(data => alert("Saved! Share ID: " + data.id));
        }

        function loadRecording() {
            const id = document.getElementById("loadId").value.trim();
            if (!id) return alert("Please enter an ID.");
            fetch(`/load/${id}`)
                .then(res => res.json())
                .then(data => {
                    recording = data;
                    alert("Recording loaded. Press 'Play Recording' to hear it.");
                })
                .catch(() => alert("Failed to load recording."));
        }
    </script>
</body>
</html>
""")

@app.route("/save", methods=["POST"])
def save():
    sequence = request.json
    sequence_id = str(uuid.uuid4())
    with open(os.path.join(SEQUENCE_STORE, f"{sequence_id}.json"), "w") as f:
        json.dump(sequence, f)
    return jsonify({"id": sequence_id})

@app.route("/load/<sequence_id>", methods=["GET"])
def load(sequence_id):
    path = os.path.join(SEQUENCE_STORE, f"{sequence_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            sequence = json.load(f)
        return jsonify(sequence)
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)
