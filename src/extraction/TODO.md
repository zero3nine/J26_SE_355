                     CLEANED JOB CSV
                           │
                           ▼
                    job_description
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
      LEXICAL EXTRACTOR          SEMANTIC EXTRACTOR
             │                           │
             │                           │
      keyword/pattern              contextual meaning
      matching                     interpretation
             │                           │
             ▼                           ▼
       extracted skills             extracted skills
             │                           │
             └─────────────┬─────────────┘
                           │
                           ▼
                  CANONICAL SKILL FORMAT
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
          lexical_dataset.csv   semantic_dataset.csv
                 │                   │
                 └─────────┬─────────┘
                           ▼
                    HUMAN GROUND TRUTH
                           │
                           ▼
                 Precision / Recall / F1
                           │
                           ▼
                          RQ1


STEP 1
Define exactly what counts as a skill
        ↓
STEP 2
Create the skill taxonomy / canonical skill list
        ↓
STEP 3
Create a small human-annotated ground-truth dataset
        ↓
STEP 4
Design the common extraction interface
        ↓
STEP 5
Build the lexical extractor
        ↓
STEP 6
Build the semantic extractor
        ↓
STEP 7
Apply common normalisation
        ↓
STEP 8
Evaluate both against ground truth
        ↓
STEP 9
Calculate Precision / Recall / F1
        ↓
STEP 10
Build the prototype UI / comparison output
        ↓
STEP 11
Export lexical + semantic datasets
        ↓
             RQ1 RESULT