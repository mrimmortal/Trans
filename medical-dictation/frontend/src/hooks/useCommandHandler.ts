// hooks/useCommandHandler.ts
'use client';

import { useCallback, useEffect, useRef } from 'react';
import { VoiceCommand } from '../types';

interface CommandHandlerOptions {
  // Editing commands
  onUndo?: () => void;
  onRedo?: () => void;
  onCopy?: () => void;
  onCut?: () => void;
  onPaste?: () => void;
  onSelectAll?: () => void;
  onDeleteLastWord?: () => void;
  onDeleteLastSentence?: () => void;
  onDeleteLastParagraph?: () => void;
  onClearAll?: () => void;
  
  // Navigation commands
  onScrollUp?: () => void;
  onScrollDown?: () => void;
  onGoToStart?: () => void;
  onGoToEnd?: () => void;
  
  // Control commands
  onSave?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  
  // General handler
  onAnyCommand?: (command: VoiceCommand) => void;
}

/**
 * Hook to handle voice commands that require frontend/UI actions.
 * 
 * Server-side processed (text is already modified):
 * - Punctuation: "period" → "."
 * - Formatting: "bold" → "**"
 * - Templates: "insert vitals" → full template
 * 
 * Client-side processed (needs UI action):
 * - Undo/Redo, Copy/Cut/Paste
 * - Save, Scroll, Navigation
 * - Start/Stop recording
 */
export function useCommandHandler(
  commands: VoiceCommand[],
  options: CommandHandlerOptions
) {
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const handleCommand = useCallback((cmd: VoiceCommand) => {
    const opts = optionsRef.current;
    
    // Call general handler
    opts.onAnyCommand?.(cmd);

    // Handle specific commands
    switch (cmd.action) {
      // ══════════════════════════════════════════════════════════
      // EDITING COMMANDS
      // ══════════════════════════════════════════════════════════
      case 'undo':
        if (opts.onUndo) {
          opts.onUndo();
        } else {
          document.execCommand('undo');
        }
        break;

      case 'redo':
        if (opts.onRedo) {
          opts.onRedo();
        } else {
          document.execCommand('redo');
        }
        break;

      case 'copy':
        if (opts.onCopy) {
          opts.onCopy();
        } else {
          document.execCommand('copy');
        }
        break;

      case 'cut':
        if (opts.onCut) {
          opts.onCut();
        } else {
          document.execCommand('cut');
        }
        break;

      case 'paste':
        if (opts.onPaste) {
          opts.onPaste();
        } else {
          navigator.clipboard.readText().then(text => {
            // Handle paste through callback if available
          }).catch(() => {
            document.execCommand('paste');
          });
        }
        break;

      case 'select_all':
        if (opts.onSelectAll) {
          opts.onSelectAll();
        } else {
          document.execCommand('selectAll');
        }
        break;

      case 'delete_last_word':
        opts.onDeleteLastWord?.();
        break;

      case 'delete_last_sentence':
        opts.onDeleteLastSentence?.();
        break;

      case 'delete_last_paragraph':
        opts.onDeleteLastParagraph?.();
        break;

      case 'clear_all':
        opts.onClearAll?.();
        break;

      // ══════════════════════════════════════════════════════════
      // NAVIGATION COMMANDS
      // ══════════════════════════════════════════════════════════
      case 'scroll_up':
        opts.onScrollUp?.();
        break;

      case 'scroll_down':
        opts.onScrollDown?.();
        break;

      case 'go_to_start':
        opts.onGoToStart?.();
        break;

      case 'go_to_end':
        opts.onGoToEnd?.();
        break;

      // ══════════════════════════════════════════════════════════
      // CONTROL COMMANDS
      // ══════════════════════════════════════════════════════════
      case 'save':
        opts.onSave?.();
        break;

      case 'pause':
        opts.onPause?.();
        break;

      case 'resume':
        opts.onResume?.();
        break;

      default:
        console.log('[CommandHandler] Unhandled command:', cmd.action);
    }
  }, []);

  // Process commands when they change
  useEffect(() => {
    if (commands.length > 0) {
      commands.forEach(handleCommand);
    }
  }, [commands, handleCommand]);
}