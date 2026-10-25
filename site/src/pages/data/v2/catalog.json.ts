import { publicationFor } from '../../../lib/publication';
import question from '../../../../../catalog/questions/Q-ENSO-001/question.json';
import { newQuestions } from '../../../lib/newQuestions';
export function GET() {
  const records = [question, ...newQuestions].map(q => ({...q, statuses:{...q.statuses, publication:publicationFor(q.id)?.publication_status || q.statuses.publication}, publication_record:publicationFor(q.id)}));
  return new Response(JSON.stringify({schema_version:'2.0',records},null,2), {headers:{'Content-Type':'application/json'}});
}
