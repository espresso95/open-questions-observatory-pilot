import registry from '../../../publication/releases.json';
export function publicationFor(questionId: string) {
  return registry.releases.find(r => r.question_ids.includes(questionId));
}
export const releases = registry.releases;
