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
 * Used to check if a phrase is a recognized voice command.
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
 * Extracts commands, applies macros, and returns cleaned text with
 * metadata about any commands or macros found.
 *
 * Command detection priority (critical order):
 * 1. Macros (exact match or "insert <macro>")
 * 2. Entire text is a command
 * 3. Command at end of text
 * 4. Commands in middle of text
 *
 * This ordering ensures that commands are detected correctly even if
 * their names appear as substrings elsewhere.
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
              text: macro.expansion,
              commands: [],
              wasCommand: false,
              isMacro: true,
            };
          }

          // Insert variant: "insert my macro"
          if (lowercase.startsWith('insert ' + macroTrigger)) {
            return {
              text: macro.expansion,
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
      const foundCommands: Array<{
        type: 'punctuation' | 'format' | 'action' | 'control';
        value?: string;
        action?: string;
      }> = [];

      // ============================================================
      // STEP 3: Check for commands at end of text
      // ============================================================
      let commandFound = true;
      while (commandFound) {
        commandFound = false;
        for (const commandKey of Object.keys(VOICE_COMMANDS)) {
          const keyLower = commandKey.toLowerCase();
          const resultLower = resultText.toLowerCase();

          // Check if text ends with " <command>"
          if (resultLower.endsWith(' ' + keyLower)) {
            const value = VOICE_COMMANDS[commandKey as CommandKey];
            // Remove the command from the end
            resultText = resultText.slice(0, -(keyLower.length + 1));

            let commandType: 'punctuation' | 'format' | 'action' | 'control';
            if (commandKey in PUNCTUATION_COMMANDS) {
              commandType = 'punctuation';
              // Append punctuation directly to result
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
            break; // restart loop to catch multiple end commands
          }
        }
      }

      // ============================================================
      // STEP 4: Check for commands in middle of text
      // (Only punctuation commands to avoid ambiguity)
      // ============================================================
      for (const commandKey of Object.keys(PUNCTUATION_COMMANDS)) {
        const keyLower = commandKey.toLowerCase();
        const value =
          PUNCTUATION_COMMANDS[commandKey as keyof typeof PUNCTUATION_COMMANDS];

        // Replace " <command> " with the punctuation
        const pattern = new RegExp(' ' + keyLower.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' ', 'gi');
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
