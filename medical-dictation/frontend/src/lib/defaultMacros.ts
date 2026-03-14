import { Macro } from '@/types';

/**
 * Default macros shipped with the app.
 *
 * ✅ FIX: field is `text` (was `expansion` which doesn't exist on Macro type).
 */
export const DEFAULT_MACROS: Macro[] = [
  // ── Cardiovascular ──
  {
    id: 'cv-normal-heart',
    trigger: 'normal heart exam',
    text: 'Heart: Regular rate and rhythm. Normal S1, S2. No murmurs, rubs, or gallops. No jugular venous distension.',
    category: 'Cardiovascular',
  },
  {
    id: 'cv-chest-pain',
    trigger: 'chest pain workup',
    text: 'Patient presents with chest pain. ECG obtained showing normal sinus rhythm. Troponin levels pending. Chest X-ray ordered.',
    category: 'Cardiovascular',
  },

  // ── Respiratory ──
  {
    id: 'resp-normal-lungs',
    trigger: 'normal lung exam',
    text: 'Lungs: Clear to auscultation bilaterally. No wheezes, rales, or rhonchi. Good air movement throughout. No respiratory distress.',
    category: 'Respiratory',
  },
  {
    id: 'resp-sob',
    trigger: 'shortness of breath',
    text: 'Patient reports shortness of breath. Oxygen saturation measured. Lung auscultation performed. Chest X-ray ordered.',
    category: 'Respiratory',
  },

  // ── Neurological ──
  {
    id: 'neuro-normal',
    trigger: 'normal neuro exam',
    text: 'Neurological: Alert and oriented x3. Cranial nerves II-XII intact. Motor strength 5/5 in all extremities. Sensation intact. Reflexes 2+ and symmetric.',
    category: 'Neurological',
  },
  {
    id: 'neuro-headache',
    trigger: 'headache assessment',
    text: 'Patient presents with headache. Onset, location, duration, character, and associated symptoms assessed. Neurological examination performed.',
    category: 'Neurological',
  },

  // ── Gastrointestinal ──
  {
    id: 'gi-normal-abdomen',
    trigger: 'normal abdominal exam',
    text: 'Abdomen: Soft, non-tender, non-distended. Bowel sounds present in all four quadrants. No hepatosplenomegaly. No masses palpated.',
    category: 'Gastrointestinal',
  },

  // ── Vitals ──
  {
    id: 'vitals-template',
    trigger: 'vitals template',
    text: 'Vital Signs:\nBlood Pressure: /\nHeart Rate: \nRespiratory Rate: \nTemperature: \nOxygen Saturation: %\nWeight: \nHeight: ',
    category: 'Vitals',
  },

  // ── Templates ──
  {
    id: 'tmpl-soap-note',
    trigger: 'soap note template',
    text: 'SUBJECTIVE:\nChief Complaint: \nHistory of Present Illness: \nReview of Systems: \n\nOBJECTIVE:\nVital Signs: \nPhysical Examination: \n\nASSESSMENT:\n\nPLAN:\n',
    category: 'Templates',
  },
  {
    id: 'tmpl-progress-note',
    trigger: 'progress note template',
    text: 'PROGRESS NOTE\nDate: \nPatient: \n\nSubjective: Patient reports \n\nObjective:\nVitals: \nExam: \nLabs: \n\nAssessment: \n\nPlan: \n',
    category: 'Templates',
  },
  {
    id: 'tmpl-discharge-summary',
    trigger: 'discharge summary template',
    text: 'DISCHARGE SUMMARY\n\nAdmission Date: \nDischarge Date: \nAttending Physician: \n\nAdmitting Diagnosis: \nDischarge Diagnosis: \n\nHospital Course: \n\nDischarge Medications: \n\nFollow-up Instructions: \n\nDischarge Condition: \n',
    category: 'Templates',
  },
];