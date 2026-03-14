'use client';

import { useCallback } from 'react';
import { Macro, ProcessedResult } from '../types';

/**
 * Punctuation commands that insert literal characters into the document.
 */
const PUNCTUATION_COMMANDS = {
  'period': '.',
  'full stop': '.',
  'comma': ',',
  'colon': ':',
  'semicolon': ';',
  'question mark': '?',
  'exclamation mark': '!',
  'exclamation point': '!',
  'open parenthesis': '(',
  'close parenthesis': ')',
  'hyphen': '-',
  'dash': ' - ',
} as const;

/**
 * Format commands that affect document structure.
 */
const FORMAT_COMMANDS = {
  'new line': 'newline',
  'next line': 'newline',
  'new paragraph': 'newParagraph',
  'next paragraph': 'newParagraph',
} as const;

/**
 * Editor action commands that perform operations on document content.
 */
const ACTION_COMMANDS = {
  'delete that': 'deleteLast',
  'undo that': 'undo',
  'clear all': 'clearAll',
  'select all': 'selectAll',
  'bold that': 'boldLast',
} as const;

/**
 * Recording control commands that manage the recording session.
 */
const CONTROL_COMMANDS = {
  'stop recording': 'stopRecording',
  'go to sleep': 'stopRecording',
  'pause recording': 'pauseRecording',
} as const;

/**
 * Complete map of all voice commands organized by category.
 */
export const VOICE_COMMANDS = {
  ...PUNCTUATION_COMMANDS,
  ...FORMAT_COMMANDS,
  ...ACTION_COMMANDS,
  ...CONTROL_COMMANDS,
} as const;

type CommandKey = keyof typeof VOICE_COMMANDS;

interface UseVoiceCommandsReturn {
  processText: (rawText: string, macros?: Macro[]) => ProcessedResult;
  VOICE_COMMANDS: typeof VOICE_COMMANDS;
}

/**
 * Hook for processing transcribed text and detecting voice commands.
 *
 * Command detection priority:
 * 1. Macros (exact match or "insert <macro>")
 * 2. Entire text is a command
 * 3. Command at end of text
 * 4. Punctuation commands in middle of text
 */
export function useVoiceCommands(): UseVoiceCommandsReturn {
  const processText = useCallback(
    (rawText: string, macros?: Macro[]): ProcessedResult => {
      const trimmed = rawText.trim();
      const lowercase = trimmed.toLowerCase();

      // ============================================================
      // STEP 1: Check macros first (highest priority)
      // ============================================================
      if (macros && macros.length > 0) {
        for (const macro of macros) {
          const macroTrigger = macro.trigger.toLowerCase();

          // Exact match: "my macro"
          if (lowercase === macroTrigger) {
            return {
              // ✅ FIX: was macro.expansion — Macro type field is `text`
              text: macro.text,
              commands: [],
              wasCommand: false,
              isMacro: true,
            };
          }

          // Insert variant: "insert my macro"
          if (lowercase.startsWith('insert ' + macroTrigger)) {
            return {
              // ✅ FIX: was macro.expansion — Macro type field is `text`
              text: macro.text,
              commands: [],
              wasCommand: false,
              isMacro: true,
            };
          }
        }
      }

      // ============================================================
      // STEP 2: Check if entire text is a command
      // ============================================================
      if (lowercase in VOICE_COMMANDS) {
        const commandKey = lowercase as CommandKey;
        const value = VOICE_COMMANDS[commandKey];
        let commandType: 'punctuation' | 'format' | 'action' | 'control';

        if (commandKey in PUNCTUATION_COMMANDS) {
          commandType = 'punctuation';
        } else if (commandKey in FORMAT_COMMANDS) {
          commandType = 'format';
        } else if (commandKey in ACTION_COMMANDS) {
          commandType = 'action';
        } else {
          commandType = 'control';
        }

        return {
          text: '',
          commands: [
            {
              type: commandType,
              value: commandType === 'punctuation' ? value : undefined,
              action: commandType !== 'punctuation' ? value : undefined,
            },
          ],
          wasCommand: true,
        };
      }

      let resultText = trimmed;
      const foundCommands: ProcessedResult['commands'] = [];

      // ============================================================
      // STEP 3: Check for commands at end of text
      // ============================================================
      let commandFound = true;
      while (commandFound) {
        commandFound = false;
        for (const commandKey of Object.keys(VOICE_COMMANDS)) {
          const keyLower = commandKey.toLowerCase();
          const resultLower = resultText.toLowerCase();

          if (resultLower.endsWith(' ' + keyLower)) {
            const value = VOICE_COMMANDS[commandKey as CommandKey];
            resultText = resultText.slice(0, -(keyLower.length + 1));

            let commandType: 'punctuation' | 'format' | 'action' | 'control';
            if (commandKey in PUNCTUATION_COMMANDS) {
              commandType = 'punctuation';
              resultText = resultText + value;
            } else if (commandKey in FORMAT_COMMANDS) {
              commandType = 'format';
            } else if (commandKey in ACTION_COMMANDS) {
              commandType = 'action';
            } else {
              commandType = 'control';
            }

            foundCommands.push({
              type: commandType,
              value: commandType === 'punctuation' ? value : undefined,
              action: commandType !== 'punctuation' ? value : undefined,
            });

            commandFound = true;
            break;
          }
        }
      }

      // ============================================================
      // STEP 4: Punctuation commands in middle of text
      // ============================================================
      for (const commandKey of Object.keys(PUNCTUATION_COMMANDS)) {
        const keyLower = commandKey.toLowerCase();
        const value =
          PUNCTUATION_COMMANDS[commandKey as keyof typeof PUNCTUATION_COMMANDS];

        const pattern = new RegExp(
          ' ' + keyLower.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' ',
          'gi'
        );
        if (pattern.test(resultText)) {
          resultText = resultText.replace(pattern, value);
          foundCommands.push({
            type: 'punctuation',
            value,
          });
        }
      }

      return {
        text: resultText,
        commands: foundCommands,
        wasCommand: false,
      };
    },
    []
  );

  return {
    processText,
    VOICE_COMMANDS,
  };
}