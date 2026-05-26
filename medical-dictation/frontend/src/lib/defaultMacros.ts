import { Macro } from '@/types';

/**
 * Generic default snippets shipped with the vanilla transcription template.
 * Domain wrappers can replace this file or provide their own defaults.
 */
export const DEFAULT_MACROS: Macro[] = [
  {
    id: 'meeting-summary',
    trigger: 'meeting summary',
    text: 'Summary:\n\nDecisions:\n\nOpen Questions:\n',
    category: 'General',
  },
  {
    id: 'action-items',
    trigger: 'action items',
    text: 'Action Items:\n1. \n2. \n3. ',
    category: 'General',
  },
  {
    id: 'follow-up-note',
    trigger: 'follow up note',
    text: 'Follow-up:\nOwner: \nDue Date: \nNext Step: ',
    category: 'General',
  },
  {
    id: 'email-draft',
    trigger: 'email draft',
    text: 'Subject: \n\nHi,\n\n\n\nThanks,\n',
    category: 'Writing',
  },
  {
    id: 'call-note',
    trigger: 'call note',
    text: 'Call Note:\nTopic: \nParticipants: \nNotes:\n\nNext Steps:\n',
    category: 'General',
  },
];
