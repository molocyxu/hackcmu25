import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export function cleanTextForExport(text: string): string {
  const replacements: [string, string][] = [
    ['\u2019', "'"],
    ['\u201c', '"'],
    ['\u201d', '"'],
    ['\u2013', '-'],
    ['\u2014', '--'],
    ['\u2026', '...'],
    ['\u00a0', ' '],
    ['\u200b', ''],
  ];
  
  let cleanedText = text;
  for (const [old, replacement] of replacements) {
    cleanedText = cleanedText.replace(new RegExp(old, 'g'), replacement);
  }
  return cleanedText;
}