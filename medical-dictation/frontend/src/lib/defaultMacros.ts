import { Macro } from '@/types';

export const DEFAULT_MACROS: Macro[] = [
  {
    id: 'macro-1',
    trigger: 'normal cardiac exam',
    category: 'Cardiovascular',
    expansion:
      'Heart: Regular rate and rhythm. Normal S1 and S2. No murmurs, rubs, or gallops. No jugular venous distension. Peripheral pulses intact bilaterally.',
  },
  {
    id: 'macro-2',
    trigger: 'normal respiratory exam',
    category: 'Respiratory',
    expansion:
      'Lungs: Clear to auscultation bilaterally. No wheezes, rales, or rhonchi. Respiratory effort is normal. No accessory muscle use.',
  },
  {
    id: 'macro-3',
    trigger: 'normal neuro exam',
    category: 'Neurological',
    expansion:
      'Neurological: Alert and oriented x3. Cranial nerves II-XII intact. Motor strength 5/5 in all extremities. Sensation intact. Deep tendon reflexes 2+ bilaterally. Gait is normal.',
  },
  {
    id: 'macro-4',
    trigger: 'normal abdominal exam',
    category: 'Gastrointestinal',
    expansion:
      'Abdomen: Soft, non-tender, non-distended. Bowel sounds present in all four quadrants. No hepatosplenomegaly. No masses palpated.',
  },
  {
    id: 'macro-5',
    trigger: 'soap template',
    category: 'Templates',
    expansion: `SUBJECTIVE:\n[Patient complaints and history]\n\nOBJECTIVE:\n[Physical examination findings]\n\nASSESSMENT:\n[Diagnosis and clinical impression]\n\nPLAN:\n[Treatment plan and follow-up]`,
  },
  {
    id: 'macro-6',
    trigger: 'normal vitals',
    category: 'Vitals',
    expansion:
      'Vital Signs: BP 120/80 mmHg, HR 72 bpm, RR 16 breaths/min, Temp 98.6°F (37°C), SpO2 98% on room air.',
  },
  {
    id: 'macro-7',
    trigger: 'review of systems negative',
    category: 'Templates',
    expansion: `Constitutional: No fever, chills, weight changes, or fatigue.\nHEENT: No headaches, vision changes, hearing loss, or sore throat.\nCardiovascular: No chest pain, palpitations, dyspnea on exertion, or leg swelling.\nRespiratory: No shortness of breath, cough, or wheezing.\nGastrointestinal: No nausea, vomiting, diarrhea, constipation, or abdominal pain.\nGenitourinary: No dysuria, frequency, urgency, or hematuria.\nMusculoskeletal: No joint pain, swelling, stiffness, or muscle weakness.\nNeurological: No dizziness, numbness, tingling, or changes in coordination.\nPsychiatric: No depression, anxiety, hallucinations, or suicidal ideation.\nSkin: No rashes, lesions, or color changes.`,
  },
];
