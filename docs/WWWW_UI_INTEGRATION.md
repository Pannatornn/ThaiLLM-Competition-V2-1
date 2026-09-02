# WWWW UI Integration

## Source
- Backend AI/RAG: ThaiLLM-Competition-V2-1
- UI/UX concept: wwww

## Integration direction

1. Keep ThaiLLM pipeline as the source of truth:
- retrieval
- evidence grounding
- verification
- benchmark

2. Replace the Streamlit presentation layer with React/Vite UI style from wwww.

3. Map UI modules:
- QuestionSection -> ThaiLLM ask endpoint
- AIAnswerExperience -> AnswerResult + Evidence
- CurriculumComparison -> compare()
- BenchmarkDashboard -> benchmark_gold evaluation
- ReliabilityCenter -> pipeline architecture

4. Preserve competition constraints:
- Document data only
- ThaiLLM only for document processing and answering
- Evidence citation required

## Status
Initial integration branch created.
