import fs from 'fs';
import { spawn, SpawnOptions } from 'child_process';

export interface PythonEnvConfig {
  pythonBin: string;
  pythonPath: string;
  env: Record<string, string>;
}

export function resolvePythonEnvironment(): PythonEnvConfig {
  // First check for explicit environment variable
  const fromEnv = process.env.PYTHON_BIN;
  let pythonBin = '';

  if (fromEnv && fs.existsSync(fromEnv)) {
    pythonBin = fromEnv;
  } else {
    // Check for virtual environment
    const venvPython = process.env.VIRTUAL_ENV ? `${process.env.VIRTUAL_ENV}/bin/python3` : null;
    if (venvPython && fs.existsSync(venvPython)) {
      pythonBin = venvPython;
    } else {
      // Check for conda environment
      const condaPrefix = process.env.CONDA_PREFIX;
      if (condaPrefix) {
        const condaPython = `${condaPrefix}/bin/python3`;
        if (fs.existsSync(condaPython)) {
          pythonBin = condaPython;
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
          // Try to spawn the python binary to check if it works
          if (
            (g.includes('/') && fs.existsSync(g)) ||
            (!g.includes('/') && require('child_process').spawnSync(g, ['--version']).status === 0)
          ) {
            pythonBin = g;
            break;
          }
        } catch {}
      }
      if (!pythonBin) pythonBin = 'python3'; // Final fallback
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
      .filter(([_, v]) => typeof v === 'string' && v !== undefined)
      .map(([k, v]) => [k, v as string])
  );

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
  
  return spawn(config.pythonBin, ['-c', script, ...args], {
    stdio: ['pipe', 'pipe', 'pipe'],
    cwd: workspaceRoot,
    env: config.env as NodeJS.ProcessEnv,
    ...options
  });
}