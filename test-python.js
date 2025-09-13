const { spawn } = require('child_process');
const pythonPath = '/opt/anaconda3/envs/whisper-env/bin/python3';

const proc = spawn(pythonPath, ['--version']);

proc.stdout.on('data', (data) => {
  console.log('stdout:', data.toString());
});
proc.stderr.on('data', (data) => {
  console.error('stderr:', data.toString());
});
proc.on('error', (err) => {
  console.error('error:', err);
});
proc.on('close', (code) => {
  console.log('closed with code', code);
});