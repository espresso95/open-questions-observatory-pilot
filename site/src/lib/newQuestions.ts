const files = import.meta.glob('../content/questions-v2.json', { eager: true, import: 'default' });
export const newQuestions: any[] = Object.values(files).flatMap((file: any) => file.questions || []);
const ledgers = import.meta.glob('../../../catalog/discovery/screening-ledger.json', { eager: true, import: 'default' });
export const screenedPaperCount = Object.values(ledgers).reduce((n: number, file: any) => n+(file.papers?.length || 0), 0);
