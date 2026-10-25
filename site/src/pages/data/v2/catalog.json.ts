import { publicationFor } from '../../../lib/publication';
import question from '../../../../../catalog/questions/Q-ENSO-001/question.json';
export function GET() {
  const release = publicationFor(question.id);
  return new Response(JSON.stringify({schema_version:'2.0',records:[{
    ...question,
    statuses:{...question.statuses,publication:release?.publication_status || question.statuses.publication},
    publication_record:release,
    frozen_snapshot_url:'../v1/catalog.json'
  }]},null,2), {headers:{'Content-Type':'application/json'}});
}
