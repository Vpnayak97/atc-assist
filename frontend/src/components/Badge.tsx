export default function Badge({ text, tone = 'neutral' }: { text: string; tone?: 'neutral' | 'ok' | 'warn' | 'bad' }) {
  return <span className={`badge badge-${tone}`}>{text}</span>
}