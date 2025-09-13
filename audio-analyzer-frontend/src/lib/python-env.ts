import fs from 'fs';
import { spawn, spawnSync, SpawnOptions } from 'child_process';

export interface PythonEnvConfig {
  pythonBin: string;
  pythonPath: string;
  env: Record<string, string>;
}

export function resolvePythonEnvironment(): PythonEnvConfig {
  // First check for explicit environment variable
  const fromEnv = process.env.PYTHON_BIN;
  let pythonBin = '';

  console.log('[PYTHON-ENV] Starting resolvePythonEnvironment');
  console.log('[PYTHON-ENV] process.env.PYTHON_BIN:', fromEnv);
  console.log('[PYTHON-ENV] process.env.VIRTUAL_ENV:', process.env.VIRTUAL_ENV);
  console.log('[PYTHON-ENV] process.env.CONDA_PREFIX:', process.env.CONDA_PREFIX);

  if (fromEnv && fs.existsSync(fromEnv)) {
    pythonBin = fromEnv;
    console.log('[PYTHON-ENV] Using PYTHON_BIN from env:', pythonBin);
  } else {
    // Check for virtual environment
    const venvPython = process.env.VIRTUAL_ENV ? `${process.env.VIRTUAL_ENV}/bin/python3` : null;
    if (venvPython && fs.existsSync(venvPython)) {
      pythonBin = venvPython;
      console.log('[PYTHON-ENV] Using VIRTUAL_ENV python:', pythonBin);
    } else {
      // Check for conda environment
      const condaPrefix = process.env.CONDA_PREFIX;
      if (condaPrefix) {
        const condaPython = `${condaPrefix}/bin/python3`;
        if (fs.existsSync(condaPython)) {
          pythonBin = condaPython;
          console.log('[PYTHON-ENV] Using CONDA_PREFIX python:', pythonBin);
        }
      }
    }
    // Improved fallback: check for common system Python executables
    if (!pythonBin) {
      const guesses = [
        '/usr/bin/python3',
        '/usr/local/bin/python3',
        '/opt/homebrew/bin/python3',
        'python3',
        'python',
      ];
      for (const g of guesses) {
        try {
          if (
            (g.includes('/') && fs.existsSync(g)) ||
            (!g.includes('/') && spawnSync(g, ['--version']).status === 0)
          ) {
            pythonBin = g;
            console.log('[PYTHON-ENV] Found working python guess:', pythonBin);
            break;
          }
        } catch (err) {
          console.log('[PYTHON-ENV] Error checking python guess:', g, err);
        }
      }
      if (!pythonBin) {
        pythonBin = '/Users/alexzheng414/gitstuff/hackcmu25/audio_analyzer_env/bin/python3'; // Final fallback (hardcoded)
        console.log('[PYTHON-ENV] Using hardcoded fallback python:', pythonBin);
      }
    }
  }
  
  // Determine Python path
  let pythonPath = process.env.PYTHONPATH || '';
  const pathPrefix = process.env.PATH_PREFIX || '/home/ubuntu/.local/bin';
  
  // If using virtual environment, use its site-packages
  if (process.env.VIRTUAL_ENV) {
    const venvSitePackages = `${process.env.VIRTUAL_ENV}/lib/python3.13/site-packages`;
    pythonPath = `${venvSitePackages}:${pythonPath}`;
  } else if (process.env.CONDA_PREFIX) {
    const condaSitePackages = `${process.env.CONDA_PREFIX}/lib/python3.13/site-packages`;
    pythonPath = `${condaSitePackages}:${pythonPath}`;
  } else {
    // Use user site-packages
    pythonPath = `/home/ubuntu/.local/lib/python3.13/site-packages:${pythonPath}`;
  }
  
  // Ensure all env values are strings
  const rawEnv: NodeJS.ProcessEnv = {
    ...process.env,
    PATH: `${pathPrefix}:${process.env.PATH || ''}`,
    PYTHONPATH: pythonPath,
    HOME: process.env.HOME || '/home/ubuntu',
    NODE_ENV: (process.env.NODE_ENV as 'development' | 'production' | 'test') || 'development'
  };

  const env: Record<string, string> = Object.fromEntries(
    Object.entries(rawEnv)
      .filter(([, v]) => typeof v === 'string' && v !== undefined)
      .map(([k, v]) => [k, v as string])
  );

  console.log('[PYTHON-ENV] Final pythonBin:', pythonBin);
  console.log('[PYTHON-ENV] Final pythonPath:', pythonPath);

  return {
    pythonBin,
    pythonPath,
    env
  };
}

export function spawnPython(
  script: string, 
  args: string[] = [], 
  options: Partial<SpawnOptions> = {}
) {
  const config = resolvePythonEnvironment();
  const workspaceRoot = process.cwd();
  console.log('[PYTHON-ENV] Spawning python process');
  console.log('[PYTHON-ENV] script:', script);
  console.log('[PYTHON-ENV] args:', args);
  console.log('[PYTHON-ENV] pythonBin:', config.pythonBin);
  console.log('[PYTHON-ENV] cwd:', workspaceRoot);
  console.log('[PYTHON-ENV] env:', config.env);
  return spawn(config.pythonBin, ['-c', script, ...args], {
    stdio: ['pipe', 'pipe', 'pipe'],
    cwd: workspaceRoot,
    env: config.env as NodeJS.ProcessEnv,
    ...options
  });
}