### Relevant Commands
- python -m src.extraction.run_lexical data/processed/jobs_clean.csv
- python -m src.extraction.run_semantic data/processed/jobs_clean.csv
- python -m src.extraction.evaluation.calibrate data/processed/jobs_clean.csv data/evaluation/ground_truth.csv *(evaluate multiple semantic thresholds to find the best threshold)*
- python -m src.extraction.evaluation.evaluate data/processed/jobs_clean.csv data/evaluation/ground_truth.csv --semantic-threshold 0.45 *(evaluate lexical v semantic approaches for the given threshold)*
- *uses the cleaned data from the scraper to read the description and display the related skills*


### Notes
 *the skill set will be added to the table in the respective (lexical in this case) columns in the future thus giving the necessary input for the analysis parts (prolly need job titles and related skills)*