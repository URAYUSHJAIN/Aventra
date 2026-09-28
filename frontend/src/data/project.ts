// Public project links. The repository is public; engineering docs and experiment records live on its default branch.
export const REPOSITORY_URL = 'https://github.com/URAYUSHJAIN/Aventra'
export const docUrl = (file: string) => `${REPOSITORY_URL}/blob/main/docs/${file}`
export const EXPERIMENTS_URL = `${REPOSITORY_URL}/tree/main/experiments/results`

export const ENGINEERING_DOCS: Array<{ file: string; title: string; summary: string }> = [
  { file: '04_SYSTEM_ARCHITECTURE.md', title: 'System architecture', summary: 'Components, data flow, database schema and job queue.' },
  { file: '05_ML_PIPELINE.md', title: 'ML pipeline', summary: 'Features, fingerprint, detectors, correlation, risk and evidence, as implemented.' },
  { file: '06_DATA_SOURCES_AND_PROVIDERS.md', title: 'Data sources & providers', summary: 'Permitted providers, terms, rate limits and coverage.' },
  { file: '14_API_SPECIFICATION.md', title: 'API specification', summary: 'Every endpoint, envelope, status code and error state.' },
  { file: '17_MODEL_EVALUATION.md', title: 'Model evaluation', summary: 'EXP-01 to EXP-03: commands, protocols, results and honest readings.' },
  { file: '19_TESTING.md', title: 'Testing', summary: 'ML, backend and frontend test suites and what they cover.' },
  { file: '21_DEPLOYMENT.md', title: 'Deployment', summary: 'Docker Compose, Vercel and environment configuration.' },
  { file: '25_LIMITATIONS.md', title: 'Limitations & future work', summary: 'What the system cannot do yet, and the ordered next steps.' },
]
